from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.shortcuts import render

from rdmo.projects.models import Project


def get_statistics(queryset, date_field):
    statistics = (
        queryset
        .annotate(period=TruncDay(date_field))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )

    return {
        'day': {
            'labels': [
                item['period'].isoformat()
                for item in statistics
            ],
            'values': [
                item['count']
                for item in statistics
            ],
        },
    }


@permission_required('projects.view_project', raise_exception=True)
def statistics(request):
    User = get_user_model()

    context = {
        'project_statistics': get_statistics(
            Project.objects.all(),
            'created',
        ),
        'user_statistics': get_statistics(
            User.objects.all(),
            'date_joined',
        ),
    }

    return render(
        request,
        'rdmo_plugins_statistics/statistics.html',
        context,
    )
