import pytest

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone

from rdmo.projects.models import Project


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
    assert set(payload) == {'time_charts', 'category_charts'}
    project_chart = next(chart for chart in payload['time_charts'] if chart['key'] == 'project')
    catalog_chart = next(chart for chart in payload['category_charts'] if chart['key'] == 'catalog')
    progress_chart = next(chart for chart in payload['category_charts'] if chart['key'] == 'project-progress')
    assert project_chart['total'] == 1
    assert progress_chart['statistics']['rows'] == [
        {'key': 50, 'label': '50%', 'value': 1},
    ]
    assert 'query_key' not in project_chart
    assert 'date_field' not in project_chart
    assert 'Private current project' not in str(payload)
    assert client.post(url, data={}).status_code == 405
