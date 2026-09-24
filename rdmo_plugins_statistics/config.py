from django.utils.translation import gettext_lazy as _

TIME_CHART_SETTINGS = (  # the settings that can be changed in local.py
    'chart_color',
    'empty_periods',
    'label_orientation',
)

CATEGORY_CHART_SETTINGS = (  # the settings that can be changed in local.py
    'chart_color',
    'label_orientation',
    'orientation',
)

TIME_CHART_DEFINITION = {  # our predefined chart configurations
    'projects': {
        'key': 'project',
        'type': 'time',
        'chart_color': '#7eafe0',
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Projects over time'),
        'toggle_label': _('Cumulative projects'),
        'x_axis_title': _('Date of creation'),
        'modes': (
            {
                'calculation': 'period_count',
                'source': 'created',
                'label': _('New projects'),
                'action_label': _('Show new projects'),
                'export_key': 'new',
                'dataset_label': _('Number of new projects'),
                'empty_message': _('No projects were found for this period.'),
                'y_axis_title': _('Number of new projects'),
            },
            {
                'calculation': 'cumulative_count',
                'source': 'total_over_time',
                'label': _('Total projects'),
                'action_label': _('Show total projects'),
                'export_key': 'total',
                'dataset_label': _('Total number of projects'),
                'empty_message': _('No project data is available for this period.'),
                'y_axis_title': _('Total number of projects'),
            },
        ),
    },
    'users': {
        'key': 'user',
        'type': 'time',
        'chart_color': '#65c5c4',
        'empty_periods': True,
        'label_orientation': 'auto',
        'title': _('Users over time'),
        'toggle_label': _('Cumulative users'),
        'x_axis_title': _('Date of registration'),
        'modes': (
            {
                'calculation': 'period_count',
                'source': 'registered',
                'label': _('New users'),
                'action_label': _('Show new users'),
                'export_key': 'new',
                'dataset_label': _('Number of newly registered users'),
                'empty_message': _('No user registrations were found for this period.'),
                'y_axis_title': _('Number of newly registered users'),
            },
            {
                'calculation': 'cumulative_count',
                'source': 'total_over_time',
                'label': _('Total users'),
                'action_label': _('Show total users'),
                'export_key': 'total',
                'dataset_label': _('Total number of users'),
                'empty_message': _('No user data is available for this period.'),
                'y_axis_title': _('Total number of users'),
            },
        ),
    },
}

CATEGORY_CHART_DEFINITION = {  # our predefined chart configurations
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
