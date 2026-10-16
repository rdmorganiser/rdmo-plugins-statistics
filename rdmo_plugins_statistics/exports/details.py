"""Collect and publish anonymized installation-wide reporting tables."""

import csv
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.utils import timezone

from .utils import anonymize_datetime, get_detail_settings, randomize_rows

DETAIL_COLUMNS = {
    'rdmo_projects': (
        'catalog_id', 'catalog_uri', 'catalog_title_de', 'catalog_title_en',
        'site_id', 'site_domain', 'owners_domains', 'project_owners', 'project_managers', 'project_authors',
        'project_guests', 'snapshots', 'test_project', 'child_projects', 'empty_project', 'project_values',
        'progress_total', 'progress_count',
        'collaboration_emails_domain', 'collaboration_site_domain', 'created', 'updated',
        'date', 'server_environment_name', 'anonymize',
    ),
    'rdmo_users': (
        'user_email_domain', 'user_email_associated_domain', 'member',
        'project_owner', 'project_manager', 'project_author', 'project_guest', 'date_joined',
        'last_login', 'date', 'server_environment_name', 'anonymize',
    ),
}


def get_project_value_columns(columns):
    columns = tuple(columns)
    if any(not isinstance(column, str) or not column.strip() for column in columns):
        raise ValueError('Project value column names must be nonempty strings.')
    reserved = set(columns) & set(DETAIL_COLUMNS['rdmo_projects'])
    if reserved:
        raise ValueError(f'Project value columns conflict with standard columns: {", ".join(sorted(reserved))}.')
    return columns


def collect_statistics_details(server_environment_name='rdmo', *, users=True, projects=True, collected_at=None):
    """Read current installation state; sequential reads are not a database snapshot.

    Related records are fetched in batches. The final anonymized rows require
    O(users + projects) memory for random row ordering.
    """
    from .projects import collect_project_details
    from .users import collect_user_details

    config = get_detail_settings()
    value_columns = get_project_value_columns(config['project_value_selectors']) if projects else ()
    collected_at = collected_at or datetime.now(UTC)
    metadata = {
        'date': timezone.localdate(collected_at, config['timezone']),
        'server_environment_name': server_environment_name,
        'anonymize': True,
    }
    statistics = {
        'collected_at': collected_at,
        'timezone': str(config['timezone']),
        'metadata': metadata,
    }
    if users:
        statistics['users'] = collect_user_details(config, metadata)
    if projects:
        statistics['project_value_columns'] = value_columns
        statistics['projects'] = collect_project_details(config, metadata)
    return statistics


def format_csv_value(value):
    """Use lowercase booleans and ISO dates, preserving None for QUOTE_NOTNULL."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, date):
        return value.isoformat()
    return value


def export_statistics_details_csv(statistics, output_dir):
    """Publish standard columns and explicitly configured project value columns."""
    value_columns = get_project_value_columns(statistics['project_value_columns']) if 'projects' in statistics else ()
    tz = ZoneInfo(statistics['timezone'])
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = statistics['metadata']
    collected_at = statistics['collected_at'].astimezone(UTC)
    run_id = f'{collected_at:%Y%m%dT%H%M%S%fZ}-{uuid4().hex}'
    destination = output_dir / f'run-{run_id}'
    tables = {}
    with TemporaryDirectory(prefix='.statistics-details-', dir=output_dir) as staging:
        staging = Path(staging)
        for key, timestamps in (
            ('projects', ('created', 'updated')),
            ('users', ('date_joined', 'last_login')),
        ):
            if key not in statistics:
                continue
            table = f'rdmo_{key}'
            rows = randomize_rows([row.copy() for row in statistics[key]])
            columns = DETAIL_COLUMNS[table]
            if key == 'projects':
                columns = (*columns, *value_columns)
            path = staging / f'{table}.csv'
            with path.open('w', encoding='utf-8', newline='') as stream:
                csv.writer(stream, lineterminator='\n').writerow(columns)
                writer = csv.writer(stream, quoting=csv.QUOTE_NOTNULL, lineterminator='\n')
                for row in rows:
                    for field in timestamps:
                        row[field] = anonymize_datetime(row[field], tz)
                    writer.writerow(format_csv_value(row[column]) for column in columns)
            # Hash incrementally so the CSV is never loaded back into memory.
            with path.open('rb') as stream:
                checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
            tables[table] = {
                'filename': path.name, 'columns': columns, 'row_count': len(rows), 'sha256': checksum,
            }
        manifest = {
            'schema_version': 1,
            'run_id': run_id,
            'server_environment_name': metadata['server_environment_name'],
            'collected_at': collected_at.isoformat(),
            'date': metadata['date'].isoformat(),
            'anonymize': True,
            'timestamp_timezone': statistics['timezone'],
            'timestamp_policy': 'local-09:09:09',
            'database_snapshot': False,
            'csv': {'encoding': 'utf-8', 'delimiter': ',', 'null': 'unquoted empty field', 'quote_non_null': True},
            'tables': tables,
        }
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        # Rename the entire directory on the same filesystem. Hidden staging
        # directories are never consumable runs, including after interruption.
        staging.rename(destination)
    return destination
