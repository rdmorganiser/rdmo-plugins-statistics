import csv

import pytest

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rdmo.projects.models import Project
from rdmo.questions.models import Catalog

from rdmo_plugins_statistics.charts import (
    compute_dashboard_charts,
    compute_dashboard_summary,
    compute_project_progress_statistics,
)
from rdmo_plugins_statistics.config import CATEGORY_CHART_DEFINITION
from rdmo_plugins_statistics.statistics import (
    compute_cumulative_date_counts,
    fetch_statistics_for_sites,
)


def test_compute_cumulative_date_counts():
    assert compute_cumulative_date_counts([
        {'date': '2025-01-01', 'count': 2},
        {'date': '2025-01-03', 'count': 3},
    ]) == [
        {'date': '2025-01-01', 'count': 2},
        {'date': '2025-01-03', 'count': 5},
    ]
    assert compute_cumulative_date_counts([]) == []


def test_dashboard_summary_uses_existing_aggregates():
    statistics = {
        'projects': {
            'total': 8,
            'progress': [
                {'percentage': 50, 'count': 3},
                {'percentage': 100, 'count': 2},
            ],
        },
        'users': {'total': 5},
        'catalogs': {
            'usage': [
                {'project_count': 4},
                {'project_count': 0},
                {'project_count': 1},
            ],
        },
    }

    assert compute_dashboard_summary(statistics) == {
        'projects': 8,
        'users': 5,
        'catalogs_in_use': 2,
        'complete_projects': 2,
    }

    statistics['projects']['progress'] = [{'percentage': 50, 'count': 3}]
    assert compute_dashboard_summary(statistics)['complete_projects'] == 0


def test_project_progress_statistics_uses_the_configured_group_size():
    statistics = [
        {'percentage': 0, 'count': 1},
        {'percentage': 4, 'count': 2},
        {'percentage': 5, 'count': 3},
        {'percentage': 99, 'count': 4},
        {'percentage': 100, 'count': 5},
    ]

    rows = compute_project_progress_statistics(
        statistics,
        CATEGORY_CHART_DEFINITION['project_progress']['progress_group_size'],
    )['rows']

    assert len(rows) == 11
    assert rows[0] == {'key': 0, 'label': '0-9%', 'value': 6}
    assert rows[1] == {'key': 10, 'label': '10-19%', 'value': 0}
    assert rows[9] == {'key': 90, 'label': '90-99%', 'value': 4}
    assert rows[10] == {'key': 100, 'label': '100%', 'value': 5}


@pytest.mark.django_db
def test_statistics_requires_site_manager(client):
    user = get_user_model().objects.create_user(username='member')
    client.force_login(user)

    response = client.get(reverse('statistics:index'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_statistics_page_uses_current_site_data(client):
    current_site = Site.objects.get_current()
    other_site = Site.objects.create(domain='other.example.com', name='Other site')
    manager = get_user_model().objects.create_user(username='manager')
    manager.role.manager.add(current_site)

    other_user = get_user_model().objects.create_user(username='other-user')
    other_user.role.member.remove(current_site)
    other_user.role.member.add(other_site)

    project = Project.objects.create(
        site=current_site,
        title='Private current project',
        progress_count=1,
        progress_total=2,
    )
    Project.objects.create(
        site=current_site,
        title='Another private current project',
        progress_count=1,
        progress_total=2,
    )
    other_project = Project.objects.create(
        site=other_site,
        title='Private other project',
        progress_count=2,
        progress_total=2,
    )
    catalog = Catalog.objects.create(
        uri_prefix='https://example.org',
        uri_path='summary-catalog',
        title_lang1='Summary catalog',
    )
    catalog.sites.set([current_site, other_site])
    project.catalog = catalog
    project.save(update_fields=['catalog'])
    other_project.catalog = catalog
    other_project.save(update_fields=['catalog'])
    client.force_login(manager)

    response = client.get(reverse('statistics:index'))

    assert response.status_code == 200
    project_chart = next(chart for chart in response.context['time_charts'] if chart['key'] == 'project')
    user_chart = next(chart for chart in response.context['time_charts'] if chart['key'] == 'user')
    catalog_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'catalog')
    progress_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'project-progress')
    expected_date = timezone.localtime(project.created).date().isoformat()

    assert project_chart['total'] == 2
    assert project_chart['title'] == 'Projects over time'
    assert project_chart['x_axis_title'] == 'Date of creation'
    assert user_chart['title'] == 'Users over time'
    assert user_chart['x_axis_title'] == 'Date of registration'
    assert response.context['summary'] == {
        'projects': 2,
        'users': 1,
        'catalogs_in_use': 1,
        'complete_projects': 0,
    }
    assert [mode['calculation'] for mode in project_chart['modes']] == ['period_count', 'cumulative_count']
    assert project_chart['statistics']['period_count']['day']['rows'] == [
        {'key': expected_date, 'label': expected_date, 'value': 2},
    ]
    assert project_chart['statistics']['cumulative_count']['day']['rows'] == [
        {'key': expected_date, 'label': expected_date, 'value': 2},
    ]
    assert user_chart['total'] == 1
    assert len(response.context['time_charts']) == 2
    assert set(catalog_chart['statistics']) == {'rows'}
    assert catalog_chart['chart_type'] == 'bar'
    assert len(progress_chart['statistics']['rows']) == 11
    assert progress_chart['statistics']['rows'][5] == {'key': 50, 'label': '50-59%', 'value': 2}
    assert progress_chart['chart_type'] == 'bar'
    assert progress_chart['orientation'] == 'vertical'
    assert progress_chart['x_axis_title'] == 'Progress (%)'
    assert progress_chart['y_axis_title'] == 'Number of projects'
    assert b'data-chart-type="bar"' in response.content
    assert b'data-chart-orientation="vertical"' in response.content
    assert response.content.count(b'data-statistics-time-controls') == 1
    assert response.content.count(b'class="statistics-data-table"') == 4
    assert response.content.count(b'role="img"') == 4
    assert response.content.count(
        b'class="statistics-summary-icon fa fa-folder" data-icon="folder" aria-hidden="true"'
    ) == 1
    assert response.content.count(
        b'class="statistics-summary-icon fa fa-users" data-icon="people" aria-hidden="true"'
    ) == 1
    assert response.content.count(b'class="btn-link statistics-mode-toggle"') == 2
    assert response.content.count(b'aria-pressed="false"') == 2
    assert b'aria-label="Cumulative projects"' in response.content
    assert b'aria-label="Cumulative users"' in response.content
    assert b'title="Show total projects"' in response.content
    assert b'title="Show total users"' in response.content
    assert response.content.count(b'class="statistics-mode-icon fa fa-toggle-off" aria-hidden="true"') == 2
    assert response.content.count(b'class="statistics-mode-option statistics-mode-option-new"') == 2
    assert response.content.count(b'class="statistics-mode-option statistics-mode-option-total"') == 2
    assert response.content.count(b'data-site-name="') == 4
    assert b'type="radio"' not in response.content
    assert response.content.count(b'class="form-control statistics-interval"') == 1
    assert b'class="form-control statistics-start-date"' in response.content
    assert b'class="form-control statistics-end-date"' in response.content
    assert response.content.count(b'class="btn btn-default statistics-export-csv"') == 4
    assert response.content.count(b'class="btn btn-default statistics-export-image"') == 4
    assert response.content.count(b'aria-label="Download PNG"') == 4
    assert b'<option value="month" selected>' in response.content
    assert b'At end' not in response.content
    assert response.content.count(b'>Displayed</strong>') == 2
    assert b'Current total' in response.content
    assert b'cumulative-user-statistics-data' not in response.content
    assert b'class="statistics-row-limit"' not in response.content
    assert 'Private current project' not in str(progress_chart)


@pytest.mark.django_db
def test_catalog_chart_includes_all_catalogs_without_a_limit_control(client):
    current_site = Site.objects.get_current()
    manager = get_user_model().objects.create_user(username='catalog-limit-manager')
    manager.role.manager.add(current_site)

    for index in range(26):
        catalog = Catalog.objects.create(
            uri_prefix='https://example.org',
            uri_path=f'catalog-{index}',
            title_lang1=f'Catalog {index}',
        )
        catalog.sites.add(current_site)

    client.force_login(manager)
    response = client.get(reverse('statistics:index'))
    catalog_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'catalog')

    assert response.status_code == 200
    assert len(catalog_chart['statistics']['rows']) == 26
    assert b'class="statistics-row-limit"' not in response.content
    assert b'data-row-limit=' not in response.content


@pytest.mark.django_db
@override_settings(RDMO_STATISTICS={'project_progress': {'orientation': 'horizontal'}})
def test_project_progress_always_uses_vertical_axes(client):
    current_site = Site.objects.get_current()
    manager = get_user_model().objects.create_user(username='horizontal-progress-manager')
    manager.role.manager.add(current_site)
    Project.objects.create(site=current_site, title='Progress project', progress_count=1, progress_total=2)
    client.force_login(manager)

    response = client.get(reverse('statistics:index'))
    progress_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'project-progress')

    assert progress_chart['chart_type'] == 'bar'
    assert progress_chart['orientation'] == 'vertical'
    assert progress_chart['x_axis_title'] == 'Progress (%)'
    assert progress_chart['y_axis_title'] == 'Number of projects'
    assert b'data-chart-type="bar"' in response.content
    assert b'data-chart-orientation="vertical"' in response.content


def test_cumulative_user_settings_are_a_legacy_fallback():
    statistics = {
        'projects': {'total': 0, 'created': [], 'total_over_time': [], 'progress': []},
        'users': {'total': 0, 'registered': [], 'total_over_time': []},
        'catalogs': {'usage': []},
    }

    charts = compute_dashboard_charts(statistics, {
        'cumulative_users': {'chart_color': '#legacy', 'empty_periods': False},
    })
    user_chart = next(chart for chart in charts['time_charts'] if chart['key'] == 'user')
    assert user_chart['chart_color'] == '#legacy'
    assert user_chart['empty_periods'] is False

    charts = compute_dashboard_charts(statistics, {
        'cumulative_users': {'chart_color': '#legacy'},
        'users': {'chart_color': '#current'},
    })
    user_chart = next(chart for chart in charts['time_charts'] if chart['key'] == 'user')
    assert user_chart['chart_color'] == '#current'


@pytest.mark.django_db
def test_statistics_api_requires_current_site_manager(client):
    url = reverse('v1-statistics:statistics-list')

    assert client.get(url).status_code == 401

    user = get_user_model().objects.create_user(username='api-member')
    client.force_login(user)

    assert client.get(url).status_code == 403

    other_site = Site.objects.create(domain='managed-elsewhere.example.com', name='Managed elsewhere')
    user.role.manager.add(other_site)

    assert client.get(url).status_code == 403


@pytest.mark.parametrize(
    'url_name',
    (
        'v1-statistics:project-statistics-list',
        'v1-statistics:user-statistics-list',
        'v1-statistics:catalog-statistics-list',
    ),
)
@pytest.mark.django_db
def test_domain_statistics_apis_require_current_site_manager(client, url_name):
    url = reverse(url_name)

    assert client.get(url).status_code == 401

    user = get_user_model().objects.create_user(username=f'{url_name}-member')
    client.force_login(user)

    assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_statistics_api_returns_current_site_aggregates(client):
    current_site = Site.objects.get_current()
    other_site = Site.objects.create(domain='api-other.example.com', name='API other site')
    manager = get_user_model().objects.create_user(username='api-manager')
    manager.role.manager.add(current_site)
    Project.objects.create(
        site=current_site,
        title='Private current project',
        progress_count=1,
        progress_total=2,
    )
    Project.objects.create(
        site=other_site,
        title='Private other project',
        progress_count=2,
        progress_total=2,
    )
    client.force_login(manager)
    url = reverse('v1-statistics:statistics-list')

    response = client.get(url, {'site': other_site.pk})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'projects', 'users', 'catalogs'}
    assert payload['projects']['total'] == 1
    assert payload['projects']['total_over_time'][-1]['count'] == 1
    assert payload['projects']['progress'] == [{'percentage': 50, 'count': 1}]
    assert payload['catalogs'] == {'usage': []}
    assert 'Private current project' not in str(payload)
    assert client.post(url, data={}).status_code == 405


@pytest.mark.django_db
def test_domain_statistics_apis_compose_the_aggregate_response(client):
    current_site = Site.objects.get_current()
    manager = get_user_model().objects.create_user(username='domain-api-manager')
    manager.role.manager.add(current_site)
    Project.objects.create(
        site=current_site,
        title='Domain API project',
        progress_count=1,
        progress_total=4,
    )
    client.force_login(manager)

    aggregate = client.get(reverse('v1-statistics:statistics-list')).json()
    projects = client.get(reverse('v1-statistics:project-statistics-list')).json()
    users = client.get(reverse('v1-statistics:user-statistics-list')).json()
    catalogs = client.get(reverse('v1-statistics:catalog-statistics-list')).json()

    assert set(projects) == {'total', 'created', 'total_over_time', 'progress'}
    assert set(users) == {'total', 'registered', 'total_over_time'}
    assert set(catalogs) == {'usage'}
    assert aggregate == {'projects': projects, 'users': users, 'catalogs': catalogs}


@pytest.mark.django_db
def test_statistics_can_be_fetched_for_multiple_sites(client, tmp_path):
    current_site = Site.objects.get_current()
    other_site = Site.objects.create(domain='statistics-other.example.com', name='Statistics other site')

    current_user = get_user_model().objects.create_user(username='statistics-current-user')
    current_user.role.member.add(current_site)
    other_user = get_user_model().objects.create_user(username='statistics-other-user')
    other_user.role.member.remove(current_site)
    other_user.role.member.add(other_site)
    shared_user = get_user_model().objects.create_user(username='shared-user')
    shared_user.role.member.set([current_site, other_site])
    current_user.role.member.set([current_site])
    extra_user = get_user_model().objects.create_user(username='extra-user')
    extra_user.role.member.set([other_site])

    catalog = Catalog.objects.create(uri_prefix='https://example.org', uri_path='catalog', title_lang1='=Catalog')
    catalog.sites.set([current_site, other_site])
    Project.objects.create(site=current_site, catalog=catalog, title='Current site project')
    Project.objects.create(site=other_site, catalog=catalog, title='Other site project')
    Project.objects.create(
        site=other_site, catalog=catalog, title='Second other project',
        progress_count=1, progress_total=2,
    )

    statistics = fetch_statistics_for_sites((current_site, other_site))

    assert [entry['site'] for entry in statistics] == [
        {
            'id': current_site.pk,
            'name': current_site.name,
            'domain': current_site.domain,
        },
        {
            'id': other_site.pk,
            'name': other_site.name,
            'domain': other_site.domain,
        },
    ]
    assert [entry['projects']['total'] for entry in statistics] == [1, 2]
    assert [entry['users']['total'] for entry in statistics] == [2, 3]
    assert [entry['projects']['total_over_time'][-1]['count'] for entry in statistics] == [1, 2]
    assert [entry['users']['total_over_time'][-1]['count'] for entry in statistics] == [2, 3]
    assert [entry['catalogs']['usage'][0]['project_count'] for entry in statistics] == [1, 2]

    current_user.role.manager.add(current_site)
    client.force_login(current_user)
    response = client.get(reverse('statistics:index'))
    assert response.status_code == 200
    assert response.context['time_charts'][0]['total'] == 1
    assert response.context['category_charts'][0]['statistics']['rows'][0]['value'] == 1

    call_command('export_statistics', site_id=[current_site.pk, other_site.pk], output_dir=tmp_path)

    def read_table(name):
        with (tmp_path / name).open(newline='', encoding='utf-8') as stream:
            return list(csv.DictReader(stream))

    assert [row['project_count'] for row in read_table('site_totals.csv')] == ['1', '2']
    assert [row['user_count'] for row in read_table('site_totals.csv')] == ['2', '3']
    assert [row['project_count'] for row in read_table('project_creation.csv')] == ['1', '2']
    assert [row['project_count'] for row in read_table('project_totals_over_time.csv')] == ['1', '2']
    assert [row['user_count'] for row in read_table('user_registration.csv')] == ['2', '3']
    assert [row['user_count'] for row in read_table('user_totals_over_time.csv')] == ['2', '3']
    assert [row['percentage'] for row in read_table('project_progress.csv')] == ['0', '0', '50']
    assert [row['catalog_title'] for row in read_table('catalog_usage.csv')] == ["'=Catalog", "'=Catalog"]

    empty_site = Site.objects.create(domain='empty.example.org', name='Empty')
    call_command('export_statistics', site_id=[empty_site.pk], output_dir=tmp_path)
    assert len(read_table('site_totals.csv')) == 1
    for name in (
        'project_creation.csv',
        'project_totals_over_time.csv',
        'user_registration.csv',
        'user_totals_over_time.csv',
        'project_progress.csv',
        'catalog_usage.csv',
    ):
        assert read_table(name) == []
        assert (tmp_path / name).read_text().startswith('site_id,site_name,site_domain,')
    previous = (tmp_path / 'site_totals.csv').read_bytes()
    with pytest.raises(CommandError, match='Unknown site IDs'):
        call_command('export_statistics', site_id=[empty_site.pk, 999999], output_dir=tmp_path)
    assert (tmp_path / 'site_totals.csv').read_bytes() == previous
