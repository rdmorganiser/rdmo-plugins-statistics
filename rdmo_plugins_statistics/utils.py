from django.db.models import Count, Q
from django.db.models.functions import TruncDay

from rdmo.questions.models import Catalog


def get_time_statistics(queryset, date_field):
    statistics = (
        queryset
        .annotate(period=TruncDay(date_field))
        .values('period')
        .annotate(count=Count('id'))
        .values_list('period', 'count')
        .order_by('period')
    )

    return {
        'day': {
          'rows': [
              {
                  'key': period.isoformat(),
                  'label': period.isoformat(),
                  'value': count,
              }
              for period, count in statistics
          ],
        },
    }


def get_catalog_statistics(current_site):
    statistics = (
        Catalog.objects
        .filter(sites=current_site)
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
                **({'label_suffix': ' *'} if not catalog.available else {}),
            }
            for catalog in statistics
        ],
    }
