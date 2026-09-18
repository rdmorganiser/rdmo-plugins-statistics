from django.utils.translation import gettext_lazy as _

TIME_CHART_SETTINGS = (
    'chart_color',
    'empty_periods',
    'label_orientation',
)

CATEGORY_CHART_SETTINGS = {
    'catalogs': (
        'chart_color',
        'label_orientation',
        'orientation',
    ),
    'project_progress': (
        'chart_color',
        'label_orientation',
    ),
}

TIME_CHART_DEFINITION = {
    'projects': {
        'key': 'project',
        'type': 'time',
        'calculation': 'period_count',
        'chart_color': '#7eafe0',
        'dataset_label': _('Number of projects'),
        'empty_periods': True,
        'empty_message': _('No projects were found for this period.'),
        'label_orientation': 'auto',
        'title': _('Number of projects over time'),
        'x_axis_title': _('Date of creation'),
        'y_axis_title': _('Number of projects'),
    },
    'users': {
        'key': 'user',
        'type': 'time',
        'calculation': 'period_count',
        'chart_color': '#65c5c4',
        'dataset_label': _('Number of registered users'),
        'empty_periods': True,
        'empty_message': _('No user registrations were found for this period.'),
        'label_orientation': 'auto',
        'title': _('Number of registered users over time'),
        'x_axis_title': _('Date of registration'),
        'y_axis_title': _('Number of registered users'),
    },
    'cumulative_users': {
        'key': 'cumulative-user',
        'type': 'time',
        'calculation': 'cumulative_count',
        'chart_color': '#65c5c4',
        'dataset_label': _('Number of users'),
        'empty_periods': True,
        'empty_message': _('No user data is available for this period.'),
        'label_orientation': 'auto',
        'title': _('Total users'),
        'x_axis_title': _('Date of registration'),
        'y_axis_title': _('Number of users'),
    },
}

CATEGORY_CHART_DEFINITION = {
    'catalogs': {
        'key': 'catalog',
        'type': 'category',
        'chart_type': 'bar',
        'chart_color': '#a8d37d',
        'dataset_label': _('Number of projects'),
        'empty_message': _('No catalog usage data is available.'),
        'label_orientation': 'auto',
        'note': _('* unavailable'),
        'orientation': 'horizontal',
        'title': _('Catalog usage'),
        'x_axis_title': _('Number of projects'),
        'y_axis_title': _('Catalog'),
    },
    'project_progress': {
        'key': 'project-progress',
        'type': 'category',
        'chart_type': 'bar',
        'chart_color': '#e6a15c',
        'dataset_label': _('Number of projects'),
        'empty_message': _('No project progress data is available.'),
        'label_orientation': 'auto',
        'orientation': 'vertical',
        'progress_group_size': 10,
        'title': _('Project progress'),
        'x_axis_title': _('Progress (%)'),
        'y_axis_title': _('Number of projects'),
    },
}
