from collections import Counter

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from rdmo.projects.models import Project
from rdmo.questions.models import Catalog


def annotate_and_fetch_date_counts(queryset, date_field, *, distinct=False):
    return [
        {'date': period.isoformat(), 'count': count}
        for period, count in (
            queryset.annotate(period=TruncDate(date_field)).values('period')
            .annotate(count=Count('id', distinct=distinct))
            .values_list('period', 'count').order_by('period')
        )
    ]


def fetch_project_statistics(site):
    projects = Project.objects.filter(site=site)
    created = annotate_and_fetch_date_counts(projects, 'created')
    progress = Counter()
    for count, total, project_count in (
        projects.order_by().values('progress_count', 'progress_total')
        .annotate(project_count=Count('id'))
        .values_list('progress_count', 'progress_total', 'project_count')
    ):
        percentage = round(100 * count / total) if count is not None and total else 0
        progress[percentage] += project_count
    return {
        'total': sum(row['count'] for row in created),
        'created': created,
        'progress': [
            {'percentage': percentage, 'count': progress[percentage]}
            for percentage in sorted(progress)
        ],
    }


def fetch_user_statistics(site):
    users = get_user_model().objects.filter(role__member=site)
    date_joined = annotate_and_fetch_date_counts(users, 'date_joined', distinct=True)
    return {
        'total': sum(row['count'] for row in date_joined),
        'registered': date_joined
    }


def fetch_catalog_statistics(site):
    catalogs = (
        Catalog.objects.filter(sites=site)
        .annotate(project_count=Count('projects', filter=Q(projects__site=site), distinct=True))
        .order_by('id')
    )
    return {
        'usage': [
            {
                'id': catalog.pk,
                'uri': catalog.uri,
                'title': catalog.title,
                'available': catalog.available,
                'project_count': catalog.project_count,
            }
            for catalog in catalogs
        ],
    }


def fetch_statistics(site):
    return {
        'projects': fetch_project_statistics(site),
        'users': fetch_user_statistics(site),
        'catalogs': fetch_catalog_statistics(site),
    }


def fetch_statistics_for_sites(sites):
    return [
        {'site': {'id': site.pk, 'name': site.name, 'domain': site.domain}, **fetch_statistics(site)}
        for site in sites
    ]
