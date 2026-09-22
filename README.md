# RDMO Statistics Plugin

The RDMO Statistics Plugin adds a statistics page to RDMO and displays project, user, catalog usage, and project progress data as charts.

## Features

The statistics page currently provides:

- New and cumulative project counts over time
- New and cumulative user counts over time
- RDMO-style icon toggles between new and total counts, with visible mode labels
- Catalog usage by number of projects
- Distribution of projects by ten-point progress groups
- Summary cards for projects and users
- Daily, monthly, quarterly, and yearly aggregation for the time-based charts
- Shared start and end date filters for all time-based charts
- Totals for the displayed time range and the system's overall total where applicable
- Persistent and shareable interval and date-filter selection using browser storage and URL parameters
- Accessible data tables, semantic tooltips, and explicit empty states for every chart
- Complete catalog usage display
- CSV export for every chart
- PNG image download for every chart

Access to the statistics page is restricted to site managers and controlled by the statistics.view_statistics permission.

Project, catalog statistics and user registrations are restricted to the current Django site.

## Requirements

- RDMO 2.5.x
- RDMO 3.0 compatibility is tested against the RDMO 3.0 release branch until 3.0 is published.
- Python 3.10 or later, according to the supported RDMO version

Chart.js is included with the plugin as a static asset. No npm installation or separate JavaScript build step is required.

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
    path('api/v1/', include('rdmo_plugins_statistics.urls.v1')),
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
{% url 'statistics:index' as statistics_url %}

{% if can_view_statistics and statistics_url %}
<li>
    <a href="{{ statistics_url }}">{% trans 'Statistics' %}</a>
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
        'chart_color': '#7eafe0',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'users': {
        'chart_color': '#65c5c4',
        'empty_periods': True,
        'label_orientation': 'auto',
    },
    'catalogs': {
        'chart_color': '#a8d37d',
        'label_orientation': 'auto',
        'orientation': 'horizontal',
    },
    'project_progress': {
        'chart_color': '#e6a15c',
        'label_orientation': 'auto',
    },
}
```

The chart configuration can be overridden in `rdmo-app/config/settings/local.py` using the optional `RDMO_STATISTICS` setting. Only the values that should differ from the defaults need to be specified.

The former `cumulative_users` settings key is deprecated. For compatibility, its values are used as fallbacks for missing `users` settings; explicit `users` settings take precedence. Both user-chart modes use the resulting unified settings.

All charts are displayed as bar charts. Project progress is always vertical.

Currently, the following configuration options are supported:

- `chart_color`
- `empty_periods` (time-based charts): include periods without new records when set to `True`
- `label_orientation`: `auto`, `horizontal` or `vertical` (only effective on vertical bar charts)
- `orientation` (catalog usage only): display the chart `horizontal` or `vertical`

## Displayed Statistics

By default, the time-based charts display a shortened time range to improve readability. Users can expand or further restrict the displayed data using the From and To date filters.

Each time chart has an independent toggle: off shows new records per period, on shows cumulative totals. Both mode labels remain visible beside the icon, with the active mode highlighted. Both charts start in New mode on every page load. Reset clears the dates and restores the monthly interval without changing either chart's mode.

Chart controls use the loaded RDMO styling: Bootstrap 3 with Font Awesome toggles, or Bootstrap 5 with Bootstrap Icons toggles. No additional icon library is bundled.

CSV and PNG downloads are prefixed with a sanitized version of the current site name so files from multiple RDMO sites remain identifiable.

### Projects over time

Projects belonging to the current site are grouped by their creation date. The chart can toggle between projects created in each period and the cumulative total at the end of each period.

The chart can display the data by:

- Day
- Month
- Quarter
- Year

The user can restrict the displayed data with From and To date fields. New-project mode shows the total created during the displayed period; total-project mode includes projects created before the start date in its cumulative values.

### Users over time

New users belonging to the current site are grouped by their registration date and can be filtered and aggregated in the same way as projects. The chart can toggle between users registered in each period and the cumulative total at the end of each period.

### Catalog usage

Catalogs assigned to the current site are displayed together with the number of projects from that site using each catalog. Unavailable catalogs remain included and are marked with an asterisk.

### Project progress

The project-progress bar chart groups all projects belonging to the current site into fixed ten-point ranges from 0–9% through 90–99%, with a separate 100% group. The percentage groups are shown on the x-axis and project counts on the y-axis. Projects whose interview has not started are included in the 0–9% group.

## Frontend implementation

Site-scoped queries and domain aggregates live in `rdmo_plugins_statistics.statistics`. The JSON API and server exports use these aggregates directly. The Django view passes them to `compute_dashboard_charts` in `rdmo_plugins_statistics.charts`, which adds chart settings, labels, and mode-specific display payloads.

Statistics can also be fetched separately in Python:

```python
from rdmo_plugins_statistics.statistics import (
    fetch_catalog_statistics,
    fetch_project_statistics,
    fetch_statistics,
    fetch_statistics_for_sites,
    fetch_user_statistics,
)

project_statistics = fetch_project_statistics(site)
user_statistics = fetch_user_statistics(site)
catalog_statistics = fetch_catalog_statistics(site)

statistics = fetch_statistics(site)
site_statistics = fetch_statistics_for_sites(sites)
```

Single-site functions return domain aggregates. Projects expose `total`, `created` rows (`date`, `count`), cumulative `total_over_time` rows (`date`, `count`), and `progress` rows (`percentage`, `count`). Users expose `total`, `registered` rows (`date`, `count`), and cumulative `total_over_time` rows (`date`, `count`). Catalogs expose `usage` rows (`id`, `uri`, `title`, `available`, `project_count`).

`fetch_statistics(site)` combines these under `projects`, `users`, and `catalogs`. `fetch_statistics_for_sites(sites)` accepts an iterable or queryset of sites and returns ordered per-site results with a `site` dictionary containing `id`, `name`, and `domain`. Chart settings are accepted only by the chart adapter, not by fetchers.

The aggregate and domain-specific JSON representations are available from:

- `GET /api/v1/statistics/`
- `GET /api/v1/project-statistics/`
- `GET /api/v1/user-statistics/`
- `GET /api/v1/catalog-statistics/`

All endpoints use the `statistics.view_statistics` permission and return data for the configured current site. They do not accept a site selector. Domain endpoints return the domain objects described above; the combined endpoint returns all three. Responses contain no chart colors, translated axis labels, or orientation.

The Django template serializes chart rows with Django's `json_script` filter. The bundled `statistics.js` reads that data and creates the charts with Chart.js.


The frontend code:

- Groups daily backend data into the selected interval
- Filters all time-based charts with one validated date range
- Toggles project and user charts between new and cumulative totals
- Updates charts without reloading the page
- Stores the selected interval and date filters in `localStorage` and the page URL
- Draws values above vertical bars or beside horizontal bars
- Sizes and scrolls bar charts according to their orientation and number of entries
- Uses the currently displayed rows for charts, HTML tables, totals, and CSV exports

## Migration from earlier versions

The refactored statistics plugin replaces the previous row-level REST implementation with a permission-protected dashboard and aggregate APIs.

The previous row-level response formats are no longer provided. The following paths now return domain aggregates:

- `/api/v1/project-statistics/`
- `/api/v1/user-statistics/`

The `/api/v1/statistics/` endpoint returns the combined domain aggregates, while `/api/v1/catalog-statistics/` provides catalog usage. This also intentionally replaces the intermediate `time_charts`/`category_charts` API contract. Consumers of that contract must migrate; only the HTML dashboard uses chart payloads.

If an installation depends on one of the old endpoints, it should remain on the previous plugin version until that integration has been migrated.

## Exporting statistics on a server

Run the management command from the configured RDMO installation:

```bash
python manage.py export_statistics --output-dir /srv/rdmo/statistics
python manage.py export_statistics --site-id 1 --site-id 2 --output-dir /srv/rdmo/statistics
python manage.py export_statistics --all-sites --output-dir /srv/rdmo/statistics
```

With no site option, only the current site is exported. Explicit site IDs are validated before writing; duplicate IDs are exported once. Dates are ISO dates grouped using Django's `TIME_ZONE`. All files are UTF-8 CSVs with `site_id,site_name,site_domain` as their first columns:

| File | Remaining columns |
|---|---|
| `site_totals.csv` | `project_count,user_count` |
| `project_creation.csv` | `date,project_count` |
| `project_totals_over_time.csv` | `date,project_count` |
| `user_registration.csv` | `date,user_count` |
| `user_totals_over_time.csv` | `date,user_count` |
| `project_progress.csv` | `percentage,project_count` |
| `catalog_usage.csv` | `catalog_id,catalog_uri,catalog_title,available,project_count` |

Empty tables retain their headers. Spreadsheet formula prefixes in text are escaped with a leading apostrophe; numeric values are not escaped. Catalog IDs and site IDs identify records within this RDMO database; cross-installation imports need a source identifier supplied by the pipeline.

Each run replaces these seven files with the latest state and leaves unrelated files alone. All files are prepared before replacement, but replacement is atomic only per file, not for the whole batch. Upload only after the command exits successfully, and avoid overlapping exports to the same directory. Fetches are sequential and are not a transactionally consistent snapshot during concurrent database updates.

Example daily cron entry (adjust paths and supply your normal Django settings environment):

```cron
0 2 * * * cd /srv/rdmo && .venv/bin/python manage.py export_statistics --all-sites --output-dir /srv/rdmo/statistics
```

These exports describe current records and site assignments. Creation, registration, and cumulative series exclude deleted records; progress and catalog usage describe the current state. The cumulative files are derived from currently existing records and do not reconstruct immutable historical snapshots. CI upload and Metabase ingestion are managed outside this plugin.

## Development

Test setup and development fixture tools are documented in [`tests/README.md`](tests/README.md).

Update the committed Chart.js browser build and license from a source checkout:

```bash
python scripts/update_chartjs.py 4.5.1
```

The updater downloads the exact npm release from jsDelivr and validates both files before replacing the existing assets. Review and commit the resulting diff.

## Uninstallation

Remove the package:

```bash
pip uninstall rdmo-plugins-statistics
```

Then remove all plugin references from the RDMO configuration:

1. Remove `'rdmo_plugins_statistics'` from `INSTALLED_APPS`.
2. Remove `path('statistics/', include('rdmo_plugins_statistics.urls'))` from `urlpatterns`.
3. Remove `path('api/v1/', include('rdmo_plugins_statistics.urls.v1'))` from `urlpatterns`.
4. Remove the Statistics navigation entry from your theme override (`rdmo_theme/templates/core/base_navigation.html`).

All entries must be removed. Otherwise, Django will still try to import the uninstalled package and the application will not start.
