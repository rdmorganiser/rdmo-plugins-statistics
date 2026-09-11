import csv

import pytest

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from rdmo.projects.models import Project
from rdmo.questions.models import Catalog

from rdmo_plugins_statistics.statistics import (
    fetch_catalog_statistics_for_sites,
    fetch_project_statistics_for_sites,
    fetch_statistics_for_sites,
    fetch_user_statistics_for_sites,
)


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
    Project.objects.create(
        site=other_site,
        title='Private other project',
        progress_count=2,
        progress_total=2,
    )
    client.force_login(manager)

    response = client.get(reverse('statistics:index'))

    assert response.status_code == 200
    project_chart = next(chart for chart in response.context['time_charts'] if chart['key'] == 'project')
    user_chart = next(chart for chart in response.context['time_charts'] if chart['key'] == 'user')
    catalog_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'catalog')
    progress_chart = next(chart for chart in response.context['category_charts'] if chart['key'] == 'project-progress')
    expected_date = timezone.localtime(project.created).date().isoformat()

    assert project_chart['total'] == 2
    assert project_chart['statistics']['day']['rows'] == [
        {'key': expected_date, 'label': expected_date, 'value': 2},
    ]
    assert user_chart['total'] == 1
    assert set(catalog_chart['statistics']) == {'rows'}
    assert progress_chart['statistics']['rows'] == [
        {'key': 50, 'label': '50%', 'value': 2},
    ]
    assert 'Private current project' not in str(progress_chart)


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

    assert set(projects) == {'total', 'created', 'progress'}
    assert set(users) == {'total', 'registered'}
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
    assert [entry['catalogs']['usage'][0]['project_count'] for entry in statistics] == [1, 2]
    for fetcher, domain in (
        (fetch_project_statistics_for_sites, 'projects'),
        (fetch_user_statistics_for_sites, 'users'),
        (fetch_catalog_statistics_for_sites, 'catalogs'),
    ):
        assert fetcher((current_site, other_site)) == [
            {'site': entry['site'], **entry[domain]} for entry in statistics
        ]
    assert fetch_project_statistics_for_sites(()) == []
    assert fetch_user_statistics_for_sites(()) == []
    assert fetch_catalog_statistics_for_sites(()) == []

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
    assert [row['user_count'] for row in read_table('user_registration.csv')] == ['2', '3']
    assert [row['percentage'] for row in read_table('project_progress.csv')] == ['0', '0', '50']
    assert [row['catalog_title'] for row in read_table('catalog_usage.csv')] == ["'=Catalog", "'=Catalog"]

    empty_site = Site.objects.create(domain='empty.example.org', name='Empty')
    call_command('export_statistics', site_id=[empty_site.pk], output_dir=tmp_path)
    assert len(read_table('site_totals.csv')) == 1
    for name in ('project_creation.csv', 'user_registration.csv', 'project_progress.csv', 'catalog_usage.csv'):
        assert read_table(name) == []
        assert (tmp_path / name).read_text().startswith('site_id,site_name,site_domain,')
    previous = (tmp_path / 'site_totals.csv').read_bytes()
    with pytest.raises(CommandError, match='Unknown site IDs'):
        call_command('export_statistics', site_id=[empty_site.pk, 999999], output_dir=tmp_path)
    assert (tmp_path / 'site_totals.csv').read_bytes() == previous
