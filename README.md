# RDMO Statistics Plugin

The RDMO Statistics Plugin adds a statistics page to RDMO and displays project, user, catalog usage, and project progress data as charts.

## Features

The statistics page currently provides:

- New and cumulative project counts over time
- New and cumulative user counts over time
- RDMO-style icon toggles between new and total counts, with visible mode labels
- Catalog usage by number of projects
- Distribution of projects by ten-point progress groups
- Catalog selection for the project-progress distribution
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
- Python 3.12 or later, according to the supported RDMO version

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
        'orientation': 'vertical',
    },
}
```

The chart configuration can be overridden in `rdmo-app/config/settings/local.py` using the optional `RDMO_STATISTICS` setting. Only the values that should differ from the defaults need to be specified.

All charts are displayed as bar charts. Catalog usage defaults to horizontal, and project progress defaults to vertical. Time based charts are always displayed with vertical bars.

Currently, the following configuration options are supported:

- `chart_color`
- `empty_periods` (time-based charts): hide periods without new records when set to `False`
- `label_orientation`: `auto`, `horizontal` or `vertical` (only effective on vertical bar charts)
- `orientation` (category charts): display the chart `horizontal` or `vertical`

## Displayed Statistics

By default, the time-based charts display a shortened time range to improve readability. Users can expand or further restrict the displayed data using the From and To date filters.

Each time chart has an independent toggle: off shows new records per period, on shows cumulative totals. Both mode labels remain visible beside the icon, with the active mode highlighted. Both charts start in New mode on every page load. The From and To dates can be cleared independently using the cross inside each field. Reset clears both dates, restores the monthly interval, and selects All catalogs without changing either chart's mode.

Chart controls use the loaded RDMO styling: Bootstrap 3 with Font Awesome toggles, or Bootstrap 5 with Bootstrap Icons toggles. No additional icon library is bundled.

CSV and PNG downloads are prefixed with a sanitized version of the current site name so files from multiple RDMO sites remain identifiable.

### Projects over time

Projects belonging to the current site are grouped by their creation date. The chart can toggle between projects created in each period and the cumulative total at the end of each period.

The chart can display the data by:

- Day
- Month
- Quarter
- Year

The user can restrict the displayed data with From and To date fields. New-project mode shows the total created during the displayed period; total-project mode displays the cumulative totals for that period, including projects created before the From date. The same rule applies to registered users in cumulative mode. The Current total remains the site's overall total.

### Users over time

New users belonging to the current site are grouped by their registration date and can be filtered and aggregated in the same way as projects. The chart can toggle between users registered in each period and the cumulative total at the end of each period.

### Catalog usage

Catalogs assigned to the current site are displayed together with the number of projects from that site using each catalog. Unavailable catalogs remain included and are marked with an asterisk.

The Absolute / Relative (%) toggle switches between project counts and each catalog's share of the projects represented in this chart, after applying the date filters. Projects without a catalog are excluded from this denominator.

Catalog statistics provide site-wide reporting under `statistics.view_statistics`. Catalogs assigned to the site are included even when restricted to user groups or unavailable for new projects. Project-picker visibility and catalog editor permissions do not restrict this reporting scope. Both the selector and API validation restrict catalogs to the current site; the filter serializer obtains that site from the server configuration. Unknown, unassigned, and other-site catalog IDs receive the same validation error, without catalog details. Projects are independently restricted to the current site, including when a catalog is shared by multiple sites.

### Project progress

The project-progress bar chart groups all projects belonging to the current site into fixed ten-point ranges from 0–9% through 90–99%, with a separate 100% group. The percentage groups are shown on the x-axis and project counts on the y-axis. Projects whose interview has not started are included in the 0–9% group.

Its independent Absolute / Relative (%) toggle switches the project counts to each progress group's percentage of the projects matching the date and catalog filters. Both charts default to Absolute. The selected mode is preserved when filters change or Reset is used. Relative values are displayed to one decimal place, so rounded percentages may not sum to exactly 100%. Tooltips, data tables, CSV downloads, and PNG downloads follow the selected mode; relative export filenames include `relative`, and CSV values are numeric percentages under a `Projects (%)` heading.

The Catalog dropdown filters this distribution to projects using a selected catalog. It defaults to All catalogs, which includes projects without a catalog. Unavailable catalogs remain selectable and are marked with an asterisk. The selection combines with the shared From and To filters: these select projects by creation date, while progress represents their current state. Clearing either date individually preserves the catalog selection; overall Reset and reloading the page restore All catalogs. Reset remains available whenever a specific catalog is selected. Catalog Usage and the time charts are unaffected by the catalog selection. The data table and downloads reflect the filtered distribution, and filenames include the selected catalog's ID and title.

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

The dashboard also uses `GET /api/v1/statistics/projects/` with optional `from`, `to`, and `catalog` parameters. Dates are inclusive ISO creation dates; `catalog` is the ID of a catalog assigned to the current site. Invalid selections return HTTP 400. The response contains `catalog` usage rows filtered by dates and `project_progress` distribution rows filtered by dates and catalog. Omitting `catalog` includes all projects on the site.


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

## Detailed anonymized reporting exports

For the installation-wide reporting tables used by Metabase, run:

```bash
python manage.py export_statistics_details \
    --server-environment-name rdmo \
    --output-dir /srv/rdmo/statistics-details
```

`--output-dir` is required. `--server-environment-name` defaults to `rdmo` and
sets the source label used by your reporting pipeline, for example `rdmo-test`
or `rdmo-dev`. The CSV column and manifest key are `server_environment_name`.

By default both datasets are exported. Use `--users` for accounts only,
`--projects` for projects only, or both flags for both datasets. Unselected
datasets are neither queried nor written.

This command reads the configured RDMO database through the ORM and needs no API
token. The account dataset includes every current account, including inactive,
staff, admin, unassigned, and multi-site accounts. The project dataset includes
every current project across all sites.
Each account and project appears once. This differs from the site scope of the
dashboard, aggregate APIs, and seven-file `export_statistics` command.

Anonymization is mandatory. There is no command option, setting, raw-data mode,
or caller-supplied random seed to disable it. Both collection and CSV writing
apply the same hard-coded anonymization: shuffled row order, the fixed
`09:09:09` record time, and `anonymize` set to `true`.
Account columns and standard project columns are fixed in the
plugin; additional project-value columns must be explicitly configured. Other
input fields are not written. Authentication queries select only the fields
needed for these statistics, excluding passwords, usernames, and personal names.

Each successful invocation prints the path to a new `run-...` directory inside
the output directory. It contains:

- `rdmo_projects.csv`: 25 standard columns plus configured project-value columns,
  one row per project (when selected)
- `rdmo_users.csv`: 12 columns, one row per account (when selected)
- `manifest.json`: schema version, run ID, source label, collection timestamp/date,
  timestamp policy, file names, ordered columns, row counts, and SHA-256 checksums

The files are prepared in a hidden staging directory. Publishing renames the
entire directory on the same filesystem, so consumers see all selected files and
the manifest together. Only selected tables appear in the manifest. Import only
completed `run-...` directories after command success; ignore hidden staging
directories, including any left after a process
is killed. Existing runs are retained, so the deployment must arrange retention.
Empty datasets produce header-only CSVs with zero counts in the manifest. The
manifest identifies the source even when both datasets are empty.

### Ordered columns and CSV contract

Standard project columns:

```csv
catalog_id,catalog_uri,catalog_title_de,catalog_title_en,site_id,site_domain,owners_domains,project_owners,project_managers,project_authors,project_guests,snapshots,test_project,child_projects,empty_project,project_values,progress_total,progress_count,collaboration_emails_domain,collaboration_site_domain,created,updated,date,server_environment_name,anonymize
```

Configured project-value columns are appended in configuration order. They also
appear in the manifest and in header-only exports when no projects exist.
Their names must be nonempty strings and cannot match standard project columns.

Account columns:

```csv
user_email_domain,user_email_associated_domain,member,project_owner,project_manager,project_author,project_guest,date_joined,last_login,date,server_environment_name,anonymize
```

Files are UTF-8, comma-separated CSV without an index.
Missing values use Python `None` and are written as empty CSV fields by the
standard CSV writer. Booleans are `true`/`false`, dates are ISO dates, and
timestamps include a UTC offset. Text is preserved with standard CSV quoting
for embedded commas, quotes, and newlines.

Neither file includes user/project identifiers, a `random_id` flag, or an index
column. Rows are shuffled independently for each export; their positions apply
only within that file. `anonymize` is always `true`. Real site and catalog IDs
are retained.
Usernames, personal names, full email addresses, project titles/descriptions,
and source user/project IDs are not exported as columns. Domains and calendar
dates are retained for reporting. Explicitly selected project answer text is also
retained and can contain personal data; shuffling rows does not remove
personal information from that text. The plugin's fixed export policy is not
an access restriction on administrators who can change its code or query the
source database directly.

Project role counts count memberships; snapshots count all project snapshots;
`child_projects` counts direct children. `project_values` counts current stored
values (`snapshot=None`), including empty stored answers, when a catalog is
assigned. Without a catalog it is zero and `empty_project` is true. Attached
catalogs are included regardless of availability or site assignments.
`progress_total` and `progress_count` export the stored expected-value and
completed-value counts, preserving `None` when progress has not been computed.
`test_project` preserves the case-insensitive `test` substring check in project
titles and descriptions. `updated` comes from `Project.updated`.

Owner and collaboration site domains include both member and manager site roles,
using a complete, deduplicated, sorted union. Roles without member or manager
site memberships produce empty strings. The command assumes RDMO's normal
`user.role` relation exists. Missing roles and other unexpected errors stop the
command and show their traceback to the administrator; no partial run is
published. Account rows include member-site domains and project-role counts;
manager-site domains and editor-group flags are omitted. Project-role counts
cover the whole installation. Missing `last_login` remains `None`, so
never-logged-in accounts do not acquire artificial recent login dates.

### Export configuration and timestamp normalization

The optional `RDMO_STATISTICS_EXPORT` setting is separate from chart settings:

```python
RDMO_STATISTICS_EXPORT = {
    'timezone': 'Europe/Berlin',  # defaults to Django TIME_ZONE
    'batch_size': 500,
    'project_value_selectors': {
        'subject_areas': {
            'https://example.org/questions/catalog/my-catalog': [
                'https://example.org/domain/subject-area',
            ],
            'https://example.org/questions/catalog/another-catalog': [
                'https://example.org/domain/research-field',
            ],
        },
        'project_type': {
            'https://example.org/questions/catalog/my-catalog': [
                'https://example.org/domain/project-type',
            ],
        },
    },
}
```

Project-answer extraction is isolated in `exports/project_values.py` and
disabled by default. Each outer key in `project_value_selectors` names a CSV
column. Its value maps catalog URIs to lists of attribute URIs. The example adds
`subject_areas` and `project_type` after the standard project columns. Only
current answers for each column's configured catalog and attributes are read.
`project_values` remains the numeric answer count. Select only attributes
suitable for reporting: this text can contain personal data and is not anonymized.

Catalog and attribute URIs must match exactly. Attributes must be linked to a
question. Matching nonempty current `Value.value_and_unit` displays, including
option labels and units, are converted with `str()` and joined with `', '` in
attribute URI and answer-position order. Each configured column contains a string,
or `None` when the project's catalog is not configured for that column. An empty
attribute list or no matching nonempty answers produces `''`. With no selectors,
no extra columns are added. Display values use the active Django language.
Catalog titles are read from the configured German/English language fields
independently of UI language and without a fallback to another language. Settings use ordinary
Django configuration; configuration errors propagate to the administrator.

Source timestamps keep their year, month, and day in the configured export
timezone, with the time set to `09:09:09` and microseconds set to zero. Naive
timestamps are interpreted in that timezone. Both datasets share one collection
timestamp and date, which remain unchanged.

Email affiliation uses a domain heuristic: shorten an email domain to its last
two dot-separated components, derive
tenant labels from all site domains, and match labels as substrings. Unmatched
addresses produce `other`, independently of site membership. Duplicate tenant
labels receive `_<site_id>` after the first occurrence in domain order. Addresses
without `@` produce an empty domain for both accounts and project members, so
malformed addresses are never used as a fallback domain. Domain lists are sorted;
empty project-member email domains are retained in those lists.

### Scheduling and reporting-database ingestion

Example daily collection:

```cron
0 2 * * * cd /srv/rdmo && .venv/bin/python manage.py export_statistics_details --server-environment-name rdmo --output-dir /srv/rdmo/statistics-details
```

Related ORM data is fetched in batches, with no per-row database lookups. The
final anonymized rows require memory proportional to the number of accounts and
projects. Sequential reads describe current state and do not provide a
transactionally consistent snapshot during concurrent changes; publication of
the files together does not change that database guarantee.

CSV collection does not write the separate reporting database. The deployment
loader must validate schema version, checksums, ordered columns, counts, and the
manifest source label, and then:

1. Load the files listed in the manifest into staging tables using the CSV format
   described above.
2. In one transaction, delete existing rows for that `server_environment_name` from each
   selected reporting table and insert the staged rows with explicit column
   lists. Leave tables omitted from the manifest unchanged.
3. Preserve other source labels and existing table objects, grants, and Metabase
   configuration. A successful empty export must still clear that source's rows.

Use the source label from the manifest, not from the first data row. Replace
that source's selected rows on each import. Coordinate imports for each source
so an older run cannot replace a newer one. Validate imports and dashboards on
a test reporting database before enabling scheduled imports.

## Development

Server export code lives in `rdmo_plugins_statistics.exports`: `csv.py`
writes site aggregates, `details.py` collects and publishes detailed batches,
`users.py` and `projects.py` build their rows, `project_values.py` handles the
optional lookup of selected answer content, and `utils.py` holds shared settings
and anonymization helpers.

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

## Acknowledgements

This plugin has been developed through the [DMP4NFDI](https://dmp.services.base4nfdi.de/) project.
DMP4NFDI is a Basic Service of Base4NFDI, funded by the German Research Foundation (DFG)
under project [521453681](https://gepris.dfg.de/gepris/projekt/521453681) and is part of the German National Research Data Infrastructure (NFDI).