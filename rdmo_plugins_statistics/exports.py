import csv
from pathlib import Path
from tempfile import TemporaryDirectory

CSV_COLUMNS = {
    'site_totals': ('project_count', 'user_count'),
    'project_creation': ('date', 'project_count'),
    'user_registration': ('date', 'user_count'),
    'project_progress': ('percentage', 'project_count'),
    'catalog_usage': ('catalog_id', 'catalog_uri', 'catalog_title', 'available', 'project_count'),
}
SITE_COLUMNS = ('site_id', 'site_name', 'site_domain')


def escape_csv_cell(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + value
    return value


def export_statistics_csv(statistics, output_dir):
    """Replace the five latest-state tables from already fetched per-site aggregates."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.statistics-', dir=output_dir) as staging:
        for table, columns in CSV_COLUMNS.items():
            with (Path(staging) / f'{table}.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow((*SITE_COLUMNS, *columns))
                for entry in statistics:
                    site = entry['site']
                    prefix = (site['id'], site['name'], site['domain'])
                    if table == 'site_totals':
                        rows = [(entry['projects']['total'], entry['users']['total'])]
                    elif table == 'project_creation':
                        rows = ((row['date'], row['count']) for row in entry['projects']['created'])
                    elif table == 'user_registration':
                        rows = ((row['date'], row['count']) for row in entry['users']['registered'])
                    elif table == 'project_progress':
                        rows = ((row['percentage'], row['count']) for row in entry['projects']['progress'])
                    else:
                        rows = (
                            (row['id'], row['uri'], row['title'], row['available'], row['project_count'])
                            for row in entry['catalogs']['usage']
                        )
                    for row in rows:
                        writer.writerow(escape_csv_cell(value) for value in (*prefix, *row))

        # Replacement is atomic per file; consumers must wait for command success.
        for table in CSV_COLUMNS:
            (Path(staging) / f'{table}.csv').replace(output_dir / f'{table}.csv')
