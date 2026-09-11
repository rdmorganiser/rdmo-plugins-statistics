from django.utils.translation import gettext_lazy as _

TIME_CHART_SETTINGS = (
    'bar_color',
    'empty_periods',
    'label_orientation',
)

CATEGORY_CHART_SETTINGS = (
    'bar_color',
    'label_orientation',
    'orientation',
)

TIME_CHART_DEFINITION = {
    'projects': {
        'key': 'project',
        'type': 'time',
        'calculation': 'period_count',
        'bar_color': '#7eafe0',
        'dataset_label': _('Number of projects'),
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Number of projects'),
        'x_axis_title': _('Created'),
        'y_axis_title': _('Number of projects'),
    },
    'users': {
        'key': 'user',
        'type': 'time',
        'calculation': 'period_count',
        'bar_color': '#65c5c4',
        'dataset_label': _('Number of registered users'),
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Number of registered users'),
        'x_axis_title': _('Registered'),
        'y_axis_title': _('Number of registered users'),
    },
    'cumulative_users': {
        'key': 'cumulative-user',
        'type': 'time',
        'calculation': 'cumulative_count',
        'bar_color': '#65c5c4',
        'dataset_label': _('Number of users'),
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Total users'),
        'x_axis_title': _('Date'),
        'y_axis_title': _('Number of users'),
    },
}

CATEGORY_CHART_DEFINITION = {
    'catalogs': {
        'key': 'catalog',
        'type': 'category',
        'bar_color': '#a8d37d',
        'dataset_label': _('Number of projects'),
        'label_orientation': 'horizontal',
        'note': _('* unavailable'),
        'orientation': 'horizontal',
        'title': _('Catalog usage'),
        'x_axis_title': _('Number of projects'),
        'y_axis_title': _('Catalog'),
    },
    'project_progress': {
        'key': 'project-progress',
        'type': 'category',
        'bar_color': '#e6a15c',
        'dataset_label': _('Number of projects'),
        'label_orientation': 'horizontal',
        'orientation': 'vertical',
        'title': _('Project progress'),
        'x_axis_title': _('Progress (%)'),
        'y_axis_title': _('Number of projects'),
    },
}
