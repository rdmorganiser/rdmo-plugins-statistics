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
        'orientation': 'horizontal',
        'label_orientation': 'horizontal',
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
        'title': _('Number of projects'),
        'dataset_label': _('Number of projects'),
        'x_axis_title': _('Created'),
        'y_axis_title': _('Number of projects'),
        'bar_color': '#7eafe0',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'users': {
        'key': 'user',
        'type': 'time',
        'model': 'auth.User',
        'filters': {
            'role__member': 'current_site',
        },
        'date_field': 'date_joined',
        'title': _('Number of registered users'),
        'dataset_label': _('Number of registered users'),
        'x_axis_title': _('Registered'),
        'y_axis_title': _('Number of registered users'),
        'bar_color': '#65c5c4',
        'empty_periods': False,
        'label_orientation': 'auto',
    },
}
