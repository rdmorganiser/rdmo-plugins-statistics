from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.contrib.sites.models import Site
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from django.shortcuts import render

from rdmo.projects.models import Project
from rdmo.questions.models import Catalog


def get_time_statistics(queryset, date_field):
    statistics = (
        queryset
        .annotate(period=TruncDay(date_field))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )

    return {
        'day': {
            'rows': [
                {
                    'key': item['period'].isoformat(),
                    'label': item['period'].isoformat(),
                    'value': item['count'],
                }
                for item in statistics
            ],
        },
    }

# def get_catalog_statistics():
#     statistics = (
#         Project.objects
#         .exclude(catalog=None)
#         .values('catalog')
#         .annotate(count=Count('id'))
#         .order_by('catalog')
#     )

#     catalogs = Catalog.objects.in_bulk(
#         item['catalog'] for item in statistics
#     )

#     return {
#         'rows': [
#             {
#                 'key': item['catalog'],
#                 'label': catalogs[item['catalog']].title,
#                 'value': item['count'],
#             }
#             for item in statistics
#         ],
#     }

# def get_catalog_statistics():
#     statistics = (
#         Catalog.objects
#         .annotate(count=Count('projects'))
#         .order_by('id')
#     )

#     return {
#         'rows': [
#             {
#                 'key': catalog.id,
#                 'label': catalog.title,
#                 'value': catalog.count,
#             }
#             for catalog in statistics
#         ],
#     }

def get_catalog_statistics(current_site):
    statistics = (
        Catalog.objects
        .filter(
            sites=current_site,
            available=True,
        )
        .annotate(
            count=Count(
                'projects',
                filter=Q(projects__site=current_site),
            )
        )
        .order_by('id')
    )

    return {
        'rows': [
            {
                'key': catalog.id,
                'label': catalog.title,
                'value': catalog.count,
            }
            for catalog in statistics
        ],
    }

@permission_required('projects.view_project', raise_exception=True)
def statistics(request):
    User = get_user_model()
    current_site = Site.objects.get_current()
    print('current_site.id:', current_site.id)

    context = {
        'project_statistics': get_time_statistics(
            # Project.objects.all(),
            Project.objects.filter(site=current_site),
            'created',
        ),
        'user_statistics': get_time_statistics(
            User.objects.all(),
            'date_joined',
        ),
        'catalog_statistics': get_catalog_statistics(current_site),
    }

    return render(
        request,
        'rdmo_plugins_statistics/statistics.html',
        context,
    )
