# RDMO Statistics Plugin

The RDMO Statistics Plugin adds a statistics page to RDMO and displays project, user, and catalog data as bar charts.

## Features

The statistics page currently provides:

- Number of projects over time
- Number of registered users over time
- Catalog usage by number of projects
- Daily, monthly, quarterly, and yearly aggregation for the time-based charts
- Optional start and end date filters
- A displayed total for the currently selected time range
- Persistent interval selection for the project and user charts using browser storage

Access to the statistics page is controlled by the statistics.view_statistics permission.

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

If you are using the default RDMO navigation, also create a theme override for `core/base_navigation.html` and add a navigation entry for the Statistics page as described below.

Restart the RDMO application after changing the configuration.

## Navigation

To add the Statistics page to the RDMO navigation, override the navigation template in your RDMO application theme.

Create an override for:

```
rdmo_theme/templates/core/base_navigation.html
```

and add the following permission check where the navigation entry should appear:

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

## Displayed Statistics

### Projects

Projects belonging to the current site are grouped by their creation date.

The chart can display the data by:

- Day
- Month
- Quarter
- Year

The user can restrict the displayed data with From and To date fields. The total is recalculated whenever the interval or date range changes.

### Registered users

Users are grouped by their registration date and can be filtered and aggregated in the same way as projects.

### Catalog usage

Available catalogs assigned to the current site are displayed together with the number of projects from that site using each catalog.

## Frontend implementation

The Django view serializes the statistics with Django's `json_script` template filter. The bundled `statistics.js` reads that data and creates the charts with Chart.js 4.5.1.

The frontend code:

- Groups daily backend data into the selected interval
- Filters time-based data by start and end date
- Updates charts without reloading the page
- Stores the selected interval in `localStorage`
- Draws values above the bars
- Sorts categorical data (like projects used in catalogs) by count

## Uninstallation

Remove the package:

```bash
pip uninstall rdmo-plugins-statistics
```

Then remove both plugin references from the RDMO configuration:

1. Remove `'rdmo_plugins_statistics'` from `INSTALLED_APPS`.
2. Remove `path('statistics/', include('rdmo_plugins_statistics.urls'))` from `urlpatterns`.
3. Remove the Statistics navigation entry from your theme override (`rdmo_theme/templates/core/base_navigation.html`).

Both entries must be removed. Otherwise, Django will still try to import the uninstalled package and the application will not start.

## License

This project is licensed under the Apache License 2.0.
