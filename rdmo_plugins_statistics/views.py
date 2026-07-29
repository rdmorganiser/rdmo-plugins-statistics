# from django.shortcuts import render


# def statistics(request):
#     return render(request, 'rdmo_plugins_statistics/statistics.html')
from django.contrib.auth.decorators import permission_required
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncQuarter, TruncYear
from django.shortcuts import render

from rdmo.projects.models import Project


def get_project_statistics(truncation):
    queryset = (
        Project.objects
        .annotate(period=truncation('created'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )

    return {
        'labels': [
            item['period'].isoformat()
            for item in queryset
        ],
        'values': [
            item['count']
            for item in queryset
        ],
    }

@permission_required('projects.view_project', raise_exception=True)
def statistics(request):
    context = {
        'project_count': Project.objects.count(),
        'project_statistics': {
            'day': get_project_statistics(TruncDay),
            'month': get_project_statistics(TruncMonth),
            'quarter': get_project_statistics(TruncQuarter),
            'year': get_project_statistics(TruncYear),
        },
    }

    return render(
        request,
        'rdmo_plugins_statistics/statistics.html',
        context,
    )
