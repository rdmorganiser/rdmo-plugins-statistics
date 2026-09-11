from django.conf import settings

from .config import CATEGORY_CHART_DEFINITION, CATEGORY_CHART_SETTINGS, TIME_CHART_DEFINITION, TIME_CHART_SETTINGS

TIME_CHART_CALCULATIONS = (
    'period_count',
    'cumulative_count',
)


def get_chart_settings(name, available_settings, custom_settings):
    return {key: value for key, value in custom_settings.get(name, {}).items() if key in available_settings}


def compute_time_statistics(statistics, calculation):
    if calculation not in TIME_CHART_CALCULATIONS:
        raise ValueError(f'Unsupported time chart calculation: {calculation}')

    total = 0
    rows = []

    for item in statistics:
        period, count = item['date'], item['count']
        if calculation == 'cumulative_count':
            total += count
            value = total
        else:
            value = count

        rows.append({
            'key': period,
            'label': period,
            'value': value,
        })

    return {
        'day': {
            'rows': rows,
        },
    }


def compute_catalog_statistics(statistics):
    rows = [
        {
            'key': item['id'],
            'label': item['title'],
            'value': item['project_count'],
            'label_suffix': ' *' if not item['available'] else '',
        }
        for item in statistics
    ]
    rows.sort(key=lambda row: (-row['value'], str(row['label']), row['key']))
    return {'rows': rows}


def compute_project_progress_statistics(statistics):
    return {
        'rows': [
            {
                'key': item['percentage'],
                'label': f"{item['percentage']}%",
                'value': item['count'],
            }
            for item in statistics
        ],
    }


def compute_time_chart(name, definition, statistics, total, custom_settings):
    return {
        **definition,
        **get_chart_settings(name, TIME_CHART_SETTINGS, custom_settings),
        'statistics': compute_time_statistics(statistics, definition['calculation']),
        'total': total,
    }


def compute_category_chart(name, definition, statistics, custom_settings):
    chart_settings = get_chart_settings(name, CATEGORY_CHART_SETTINGS, custom_settings)

    chart = {
        **definition,
        **chart_settings,
        'statistics': statistics,
    }

    opposite_orientation = {
        'horizontal': 'vertical',
        'vertical': 'horizontal',
    }[definition['orientation']]

    if chart_settings.get('orientation') == opposite_orientation:
        chart['x_axis_title'], chart['y_axis_title'] = (
            chart['y_axis_title'],
            chart['x_axis_title'],
        )

    return chart


def compute_dashboard_charts(statistics, custom_settings=None):
    if custom_settings is None:
        custom_settings = getattr(settings, 'RDMO_STATISTICS', {})
    projects, users = statistics['projects'], statistics['users']
    return {
        'time_charts': [
            compute_time_chart(name, TIME_CHART_DEFINITION[name], rows, total, custom_settings)
            for name, rows, total in (
                ('projects', projects['created'], projects['total']),
                ('users', users['registered'], users['total']),
                ('cumulative_users', users['registered'], users['total']),
            )
        ],
        'category_charts': [
            compute_category_chart(name, CATEGORY_CHART_DEFINITION[name], rows, custom_settings)
            for name, rows in (
                ('catalogs', compute_catalog_statistics(statistics['catalogs']['usage'])),
                ('project_progress', compute_project_progress_statistics(projects['progress'])),
            )
        ],
    }
