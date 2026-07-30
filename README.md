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

The page is available only to authenticated users.

Project and catalog statistics are restricted to the current Django site. User registrations are counted across all users.

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

The plugin registers a Statistics entry through its Django `AppConfig`:

```python
class StatisticsConfig(AppConfig):
    name = 'rdmo_plugins_statistics'

    navigation_items = (
        {
            'name': 'statistics',
            'label': _('Statistics'),
            'url_name': 'statistics:index',
            'order': 100,
        },
    )
```

The entry is displayed when the installed RDMO version supports plugin-provided navigation items.

The page itself remains available at `/statistics/` as long as the URL configuration is registered.

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

Both entries must be removed. Otherwise, Django will still try to import the uninstalled package and the application will not start.

## License

This project is licensed under the Apache License 2.0.
