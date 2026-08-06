from django.utils.translation import gettext_lazy as _

DEFAULT_SETTINGS = {
    'projects': {
        'bar_color': '#7eafe0',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'users': {
        'bar_color': '#65c5c4',
        'empty_periods': False,
        'label_orientation': 'auto',
    },
    'catalogs': {
        'bar_color': '#a8d37d',
        'label_orientation': 'horizontal',
        'orientation': 'horizontal',
    },
}

TIME_CHART_DEFINITION = {
    'projects': {
        'key': 'project',
        'type': 'time',
        'model': 'projects.Project',
        'filters': {
            'site': 'current_site',
        },
        'date_field': 'created',
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
        'model': 'auth.User',
        'filters': {
            'role__member': 'current_site',
        },
        'date_field': 'date_joined',
        'calculation': 'period_count',
        'bar_color': '#65c5c4',
        'dataset_label': _('Number of registered users'),
        'empty_periods': False,
        'label_orientation': 'auto',
        'title': _('Number of registered users'),
        'x_axis_title': _('Registered'),
        'y_axis_title': _('Number of registered users'),
    },
    'cumulative_users': {
        'key': 'cumulative-user',
        'type': 'time',
        'model': 'auth.User',
        'filters': {
            'role__member': 'current_site',
        },
        'date_field': 'date_joined',
        'calculation': 'cumulative_count',
        'bar_color': '#65c5c4',
        'dataset_label': _('Number of users'),
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Number of users over time'),
        'x_axis_title': _('Date'),
        'y_axis_title': _('Number of users'),
    },
}
