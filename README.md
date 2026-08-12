# RDMO Statistics Plugin

The RDMO Statistics Plugin adds a statistics page to RDMO and displays project, user, catalog usage, and project progress data as bar charts.

## Features

The statistics page currently provides:

- Number of projects over time
- Number of newly registered users over time
- Cumulative number of users over time
- Catalog usage by number of projects
- Progress of individual projects
- Daily, monthly, quarterly, and yearly aggregation for the time-based charts
- Optional start and end date filters
- Totals for the displayed time range and the system's overall total where applicable
- Persistent interval and date-filter selection for time-based charts using browser storage
- CSV export for every chart

Access to the statistics page is restricted to site managers and controlled by the statistics.view_statistics permission.

Project, catalog statistics and user registrations are restricted to the current Django site.

## Requirements

- RDMO 2.5.x or later

Chart.js 4.5.1 is included with the plugin as a static asset. No npm installation or separate JavaScript build step is required.

## Installation

Install the plugin:

```bash
pip install rdmo-plugins-statistics
```

Add the plugin to `INSTALLED_APPS` in `rdmo-app/config/settings/local.py`:

```python
INSTALLED_APPS += [
    'rdmo_plugins_statistics',
]
```

Register the plugin URLs in the project URL configuration (`rdmo-app/config/urls.py`):

```python
from django.urls import include, path

urlpatterns += [
    path('statistics/', include('rdmo_plugins_statistics.urls')),
]
```

Restart the RDMO application after changing the configuration.

## Navigation

To add the Statistics page to the RDMO navigation, override the navigation template in your RDMO application theme.

Create an override for:

```
rdmo_theme/templates/core/base_navigation.html
```

and add the following where the navigation entry should appear:

```django
{% has_perm 'statistics.view_statistics' request.user as can_view_statistics %}

{% if can_view_statistics %}
<li>
    <a href="{% url 'statistics:index' %}">
        {% trans 'Statistics' %}
    </a>
</li>
{% endif %}
```

The plugin registers the `statistics.view_statistics` permission using the Django Rules framework. The same permission is enforced by the Statistics view.

## Configuration

The plugin provides sensible defaults and works without additional configuration.

The default chart configuration is:

```python
RDMO_STATISTICS = {
    'projects': {
        'bar_color': '#7eafe0',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'users': {
        'bar_color': '#65c5c4',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'cumulative_users': {
        'bar_color': '#65c5c4',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'catalogs': {
        'bar_color': '#a8d37d',
        'label_orientation': 'horizontal',
        'orientation': 'horizontal',
    },
    'project_progress': {
        'bar_color': '#e6a15c',
        'label_orientation': 'horizontal',
        'orientation': 'horizontal',
    },
}
```

The chart configuration can be overridden in `rdmo-app/config/settings/local.py` using the optional `RDMO_STATISTICS` setting. Only the values that should differ from the defaults need to be specified.

Currently, the following configuration options are supported:

- `bar_color`
- `empty_periods` (time-based charts): include periods without new records when set to `True`
- `label_orientation`
- `orientation` (category charts): display bars `horizontal` or `vertical`

## Displayed Statistics

By default, the time-based charts display a shortened time range to improve readability. Users can expand or further restrict the displayed data using the From and To date filters.

### Number of projects

Projects belonging to the current site are grouped by their creation date.

The chart can display the data by:

- Day
- Month
- Quarter
- Year

The user can restrict the displayed data with From and To date fields. The total for the displayed period is recalculated whenever the interval or date range changes.

### Number of registered users

New users belonging to the current site are grouped by their registration date and can be filtered and aggregated in the same way as projects. This chart shows how many users registered during each displayed period.

### Number of users over time

The chart shows the total number of users belonging to the current site over time.

### Catalog usage

Catalogs assigned to the current site are displayed together with the number of projects from that site using each catalog. Unavailable catalogs remain included and are marked with an asterisk.

### Project progress

Every project belonging to the current site is displayed with its interview progress as a rounded percentage. Projects whose interview has not started are shown with 0% progress.

## Frontend implementation

The Django view serializes the statistics with Django's `json_script` template filter. The bundled `statistics.js` reads that data and creates the charts with Chart.js 4.5.1.

The frontend code:

- Groups daily backend data into the selected interval
- Filters time-based data by start and end date
- Updates charts without reloading the page
- Stores the selected interval and date filters in `localStorage`
- Draws values above vertical bars or beside horizontal bars
- Sorts category charts by value in descending order
- Sizes and scrolls category charts according to their orientation and number of entries
- Exports the currently displayed chart data as CSV

## Uninstallation

Remove the package:

```bash
pip uninstall rdmo-plugins-statistics
```

Then remove both plugin references from the RDMO configuration:

1. Remove `'rdmo_plugins_statistics'` from `INSTALLED_APPS`.
2. Remove `path('statistics/', include('rdmo_plugins_statistics.urls'))` from `urlpatterns`.
3. Remove the Statistics navigation entry from your theme override (`rdmo_theme/templates/core/base_navigation.html`).

All entries must be removed. Otherwise, Django will still try to import the uninstalled package and the application will not start.
