import csv
import hashlib
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from random import Random
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import translation

from rdmo.accounts.models import Role
from rdmo.domain.models import Attribute
from rdmo.options.models import Option
from rdmo.projects.models import Membership, Project, Snapshot, Value
from rdmo.questions.models import Catalog, Question

from rdmo_plugins_statistics.exports import collect_statistics_details, export_statistics_details_csv
from rdmo_plugins_statistics.exports.details import format_csv_value
from rdmo_plugins_statistics.exports.projects import collect_project_details
from rdmo_plugins_statistics.exports.users import collect_user_details, get_sites_labels
from rdmo_plugins_statistics.exports.utils import anonymize_datetime, email_domain

COLLECTED_AT = datetime.fromisoformat('2026-10-16T12:30:00+00:00')
GERMAN_TITLE = 'Forschungsprojekte'
BASE_PROJECT_HEADER = (
    'catalog_id,catalog_uri,catalog_title_de,catalog_title_en,site_id,site_domain,'
    'owners_domains,project_owners,project_managers,project_authors,project_guests,snapshots,test_project,'
    'child_projects,empty_project,project_values,progress_total,progress_count,collaboration_emails_domain,collaboration_site_domain,'
    'created,updated,date,server_environment_name,anonymize'
)
PROJECT_HEADER = BASE_PROJECT_HEADER + ',selected_values'
USER_HEADER = (
    'user_email_domain,user_email_associated_domain,member,project_owner,'
    'project_manager,project_author,project_guest,date_joined,last_login,date,server_environment_name,anonymize'
)


@pytest.fixture
def inventory(db, settings):
    settings.LANGUAGES = [('en', 'English'), ('de', 'German')]
    settings.RDMO_STATISTICS_EXPORT = {
        'timezone': 'Europe/Berlin',
    }
    site = Site.objects.get_current()
    site.domain = 'a.alpha.edu'
    site.save()
    beta = Site.objects.create(domain='b.beta.edu', name='Beta')
    gamma = Site.objects.create(domain='c.gamma.edu', name='Gamma')
    user_model = get_user_model()
    people = [
        user_model.objects.create_user(username=f'private-user-{index}', email=email)
        for index, email in enumerate([
            'alice@dept.alpha.edu', 'bob@beta.edu', 'bad.host.example', '', 'guest@outside.invalid', 'admin@unassigned.edu',
        ])
    ]
    owner, second_owner, manager, author, guest, inactive = people
    owner.role.member.set([site, beta])
    owner.groups.add(Group.objects.create(name='editor'))
    second_owner.role.member.set([beta])
    second_owner.role.manager.add(gamma)
    manager.role.member.set([beta])
    author.role.member.clear()
    author.role.editor.add(site)
    author.groups.add(Group.objects.create(name='Editor'))
    guest.role.member.clear()
    inactive.role.member.clear()
    inactive.is_active = False
    inactive.is_staff = True
    inactive.is_superuser = True
    inactive.save()
    # User save signals can add the current site back to an existing empty role.
    inactive.role.member.clear()
    owner.date_joined = datetime.fromisoformat('2023-12-31T23:30:00+00:00')
    owner.last_login = datetime.fromisoformat('2026-10-31T12:00:00+00:00')
    user_model.objects.filter(pk=owner.pk).update(date_joined=owner.date_joined, last_login=owner.last_login)
    catalog = Catalog.objects.create(
        uri_prefix='https://example.org', uri_path='dmp', available=False,
        title_lang1='=English, "catalog"\nsecond line', title_lang2=GERMAN_TITLE,
    )
    other_catalog = Catalog.objects.create(uri_prefix='https://example.org', uri_path='other', title_lang1='Other')
    root = Project.objects.create(
        site=site, catalog=catalog, title='Private project title', description='A TeSt entry',
        progress_total=5, progress_count=3,
    )
    child = Project.objects.create(site=beta, catalog=catalog, parent=root, title='Child')
    grandchild = Project.objects.create(site=beta, catalog=other_catalog, parent=child, title='Grandchild')
    catalogless = Project.objects.create(site=None, catalog=None, title='ATTesTion')
    for user, role in zip(people[:5], ('owner', 'owner', 'manager', 'author', 'guest'), strict=True):
        Membership.objects.create(project=root, user=user, role=role)
    subject = Attribute.objects.create(uri_prefix='https://example.org', key='fachbereich')
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {'selected_values': {catalog.uri: [subject.uri]}}
    other_attribute = Attribute.objects.create(uri_prefix='https://example.org', key='other')
    Question.objects.create(uri_prefix='https://example.org', uri_path='subject', attribute=subject)
    Value.objects.create(project=root, attribute=subject, text='Engineering, "physics"\nnext line')
    Value.objects.create(project=root, attribute=subject, collection_index=1, text='  ')
    Value.objects.create(project=root, attribute=subject, collection_index=2, text='')
    Value.objects.create(project=root, attribute=other_attribute, text='Not a subject')
    Value.objects.create(project=catalogless, attribute=subject, text='Ignored without a catalog')
    snapshots = [Snapshot.objects.create(project=root, title=f'Snapshot {index}') for index in range(2)]
    Value.objects.create(project=root, snapshot=snapshots[0], attribute=subject, text='Archived subject')
    root.created = datetime.fromisoformat('2024-03-31T12:00:00+00:00')
    root.updated = datetime.fromisoformat('2025-10-31T12:00:00+00:00')
    Project.objects.filter(pk=root.pk).update(created=root.created, updated=root.updated)
    return {
        'site': site, 'beta': beta, 'gamma': gamma, 'people': people, 'catalog': catalog,
        'root': root, 'child': child, 'grandchild': grandchild, 'catalogless': catalogless, 'subject': subject,
    }


def collect():
    return collect_statistics_details('rdmo-test', collected_at=COLLECTED_AT)


def test_collects_all_accounts_once_with_site_and_project_roles(inventory):
    statistics = collect()
    assert len(statistics['users']) == get_user_model().objects.count() == 6
    by_role = {
        role: next(row for row in statistics['users'] if row[f'project_{role}'])
        for role in ('manager', 'author', 'guest')
    }
    owner = next(row for row in statistics['users'] if row['user_email_domain'] == 'alpha.edu')
    assert owner['member'] == 'a.alpha.edu, b.beta.edu'
    assert owner['user_email_associated_domain'] == 'alpha'
    assert owner['project_owner'] == 1
    assert owner['date_joined'].isoformat() == '2024-01-01T09:09:09+01:00'
    assert owner['last_login'].isoformat() == '2026-10-31T09:09:09+01:00'
    assert by_role['author']['member'] == ''
    assert by_role['manager']['user_email_domain'] == ''
    assert by_role['manager']['user_email_associated_domain'] == 'other'
    assert by_role['guest']['member'] == ''
    assert by_role['guest']['last_login'] is None
    inactive = next(row for row in statistics['users'] if row['user_email_domain'] == 'unassigned.edu')
    assert inactive['member'] == ''
    assert sum(inactive[f'project_{role}'] for role in ('owner', 'manager', 'author', 'guest')) == 0
    assert all(row['date'] == statistics['metadata']['date'] for row in statistics['users'] + statistics['projects'])


def test_project_counts_domains_and_current_values_do_not_multiply(inventory):
    statistics = collect()
    assert len(statistics['projects']) == Project.objects.count() == 4
    root = next(row for row in statistics['projects'] if row['project_values'])
    assert [root[field] for field in ('project_owners', 'project_managers', 'project_authors', 'project_guests')] == [2, 1, 1, 1]
    assert root['snapshots'] == 2
    assert root['project_values'] == 4
    assert root['progress_total'] == 5
    assert root['progress_count'] == 3
    assert root['empty_project'] is False
    assert root['child_projects'] == 1
    assert root['test_project'] is True
    assert root['site_id'] == inventory['site'].pk
    assert root['site_domain'] == 'a.alpha.edu'
    assert root['owners_domains'] == root['collaboration_site_domain'] == 'a.alpha.edu, b.beta.edu, c.gamma.edu'
    assert root['collaboration_emails_domain'] == ', alpha.edu, beta.edu, outside.invalid'
    assert root['selected_values'] == 'Engineering, "physics"\nnext line'
    assert root['catalog_uri'] == inventory['catalog'].uri
    assert root['catalog_title_de'] == GERMAN_TITLE
    assert root['catalog_title_en'] == '=English, "catalog"\nsecond line'
    assert root['created'].isoformat() == '2024-03-31T09:09:09+02:00'
    assert root['updated'].isoformat() == '2025-10-31T09:09:09+01:00'
    child = next(row for row in statistics['projects'] if row['catalog_id'] == root['catalog_id'] and not row['project_values'])
    assert child['child_projects'] == 1
    assert child['selected_values'] == ''
    assert child['empty_project'] is True
    assert child['progress_total'] is child['progress_count'] is None
    grandchild = next(row for row in statistics['projects'] if row['catalog_title_en'] == 'Other')
    assert grandchild['child_projects'] == 0
    assert grandchild['selected_values'] is None
    catalogless = next(row for row in statistics['projects'] if row['catalog_id'] is None)
    assert catalogless['project_values'] == 0
    assert catalogless['empty_project'] is True
    assert catalogless['selected_values'] is None
    assert catalogless['catalog_uri'] == catalogless['catalog_title_de'] == catalogless['catalog_title_en'] == ''
    assert catalogless['site_id'] is catalogless['site_domain'] is None
    assert catalogless['test_project'] is True


def test_configured_language_fields_ignore_active_language_and_fallback(inventory, settings):
    settings.LANGUAGES = [('de', 'German'), ('en', 'English')]
    settings.REPLACE_MISSING_TRANSLATION = True
    Catalog.objects.filter(pk=inventory['catalog'].pk).update(title_lang1='', title_lang2='Actual English')
    with translation.override('en'):
        root = next(row for row in collect()['projects'] if row['project_values'])
    assert root['catalog_title_de'] == ''
    assert root['catalog_title_en'] == 'Actual English'
    assert root['selected_values'] == 'Engineering, "physics"\nnext line'


def test_project_value_selection_requires_exact_uris(inventory, settings):
    settings.RDMO_STATISTICS_EXPORT = {
        'project_value_selectors': {
            'selected_values': {inventory['catalog'].uri: [inventory['subject'].uri]},
        },
    }
    assert next(row for row in collect()['projects'] if row['project_values'])['selected_values'].startswith('Engineering')
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {
        'selected_values': {inventory['catalog'].uri: [inventory['subject'].uri.replace('fachbereich', 'Fachbereich')]},
    }
    assert next(row for row in collect()['projects'] if row['project_values'])['selected_values'] == ''
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {
        'selected_values': {inventory['catalog'].uri.upper(): [inventory['subject'].uri]},
    }
    assert all(row['selected_values'] is None for row in collect()['projects'])
    settings.RDMO_STATISTICS_EXPORT = {}
    assert all('selected_values' not in row for row in collect()['projects'])


def test_project_values_are_only_read_for_their_catalogs_attributes(inventory, settings, monkeypatch):
    other_catalog = inventory['grandchild'].catalog
    other_attribute = Attribute.objects.get(key='other')
    code = Attribute.objects.create(uri_prefix='https://example.org', key='reporting-code')
    for attribute in (other_attribute, code):
        Question.objects.create(uri_prefix='https://example.org', uri_path=attribute.key, attribute=attribute)
    Value.objects.filter(project=inventory['root'], attribute=other_attribute).update(text='PRIVATE_FIRST_CATALOG')
    Value.objects.create(project=inventory['root'], attribute=code, text='Project code')
    Value.objects.create(project=inventory['grandchild'], attribute=other_attribute, text='Other catalog value')
    Value.objects.create(project=inventory['grandchild'], attribute=inventory['subject'], text='PRIVATE_SECOND_CATALOG')
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {
        'selected_values': {
            inventory['catalog'].uri: [inventory['subject'].uri, code.uri],
            other_catalog.uri: [other_attribute.uri],
        },
    }
    loaded_texts = []
    original_from_db = Value.from_db

    def track_loaded_values(cls, db, field_names, values):
        if 'text' in field_names:
            loaded_texts.append(values[field_names.index('text')])
        return original_from_db(db, field_names, values)

    monkeypatch.setattr(Value, 'from_db', classmethod(track_loaded_values))
    rows = collect()['projects']
    root = next(row for row in rows if row['catalog_id'] == inventory['catalog'].pk and row['project_values'])
    grandchild = next(row for row in rows if row['catalog_id'] == other_catalog.pk)
    assert root['selected_values'] == 'Engineering, "physics"\nnext line, Project code'
    assert grandchild['selected_values'] == 'Other catalog value'
    assert 'PRIVATE_FIRST_CATALOG' not in loaded_texts
    assert 'PRIVATE_SECOND_CATALOG' not in loaded_texts
    assert 'Archived subject' not in loaded_texts


def test_named_value_columns_are_joined_and_written_in_configuration_order(inventory, settings, tmp_path):
    other_attribute = Attribute.objects.get(key='other')
    Question.objects.create(uri_prefix='https://example.org', uri_path='project-type', attribute=other_attribute)
    Value.objects.filter(project=inventory['root'], attribute=other_attribute).update(text='Type A')
    Value.objects.create(project=inventory['root'], attribute=other_attribute, collection_index=1, text='Type B')
    Value.objects.create(project=inventory['grandchild'], attribute=inventory['subject'], text='Physics')
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {
        'project_type': {inventory['catalog'].uri: [other_attribute.uri]},
        'subject_areas': {
            inventory['catalog'].uri: [inventory['subject'].uri],
            inventory['grandchild'].catalog.uri: [inventory['subject'].uri],
        },
    }
    statistics = collect_statistics_details(users=False)
    root = next(row for row in statistics['projects'] if row['catalog_id'] == inventory['catalog'].pk and row['project_values'])
    grandchild = next(row for row in statistics['projects'] if row['catalog_id'] == inventory['grandchild'].catalog_id)
    child = next(row for row in statistics['projects'] if row['catalog_id'] == inventory['catalog'].pk and not row['project_values'])
    assert root['project_type'] == 'Type A, Type B'
    assert root['subject_areas'] == 'Engineering, "physics"\nnext line'
    assert grandchild['project_type'] is None
    assert grandchild['subject_areas'] == 'Physics'
    assert child['project_type'] == child['subject_areas'] == ''
    # The collected schema also governs writing if settings change afterwards.
    settings.RDMO_STATISTICS_EXPORT = {}
    completed = export_statistics_details_csv(statistics, tmp_path)
    columns = (BASE_PROJECT_HEADER + ',project_type,subject_areas').split(',')
    with (completed / 'rdmo_projects.csv').open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == columns
        rows = list(reader)
    root = next(row for row in rows if row['project_type'])
    assert root['project_type'] == 'Type A, Type B'
    assert root['subject_areas'] == 'Engineering, "physics"\nnext line'
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert manifest['tables']['rdmo_projects']['columns'] == columns


@pytest.mark.django_db
def test_empty_export_preserves_named_columns(settings, tmp_path):
    settings.RDMO_STATISTICS_EXPORT = {'project_value_selectors': {'subject_areas': {}, 'project_type': {}}}
    completed = export_statistics_details_csv(collect_statistics_details(users=False), tmp_path)
    header = BASE_PROJECT_HEADER + ',subject_areas,project_type'
    assert (completed / 'rdmo_projects.csv').read_text() == header + '\n'
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert manifest['tables']['rdmo_projects']['columns'] == header.split(',')
    assert manifest['tables']['rdmo_projects']['row_count'] == 0


@pytest.mark.parametrize('column', ['catalog_id', 'anonymize'])
@pytest.mark.parametrize('stage', ['collection', 'writing'])
def test_named_columns_cannot_override_standard_columns(inventory, settings, tmp_path, column, stage):
    if stage == 'collection':
        settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {column: {}}
        with pytest.raises(ValueError, match='conflict with standard columns'):
            collect()
    else:
        statistics = collect()
        statistics['project_value_columns'] = (column,)
        with pytest.raises(ValueError, match='conflict with standard columns'):
            export_statistics_details_csv(statistics, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_selected_values_include_option_displays_and_units(inventory):
    option = Option.objects.create(
        uri_prefix='https://example.org', uri_path='physics',
        text_lang1='Physics', view_text_lang1='Applied physics',
    )
    Value.objects.create(
        project=inventory['root'], attribute=inventory['subject'], collection_index=3, option=option,
    )
    Value.objects.create(
        project=inventory['root'], attribute=inventory['subject'], collection_index=4, text='42', unit='kg',
    )
    with translation.override('en'):
        root = next(row for row in collect()['projects'] if row['project_values'])
    assert root['selected_values'] == 'Engineering, "physics"\nnext line, Applied physics, 42 kg'


@pytest.mark.parametrize('selectors', [
    {},
    {'https://example.org/questions/dmp': []},
    {'https://example.org/unmatched-catalog': ['https://example.org/domain/fachbereich']},
    {'https://example.org/questions/dmp': ['https://example.org/domain/unmatched-attribute']},
])
def test_project_answer_content_is_not_read_without_matching_selectors(inventory, settings, selectors):
    settings.RDMO_STATISTICS_EXPORT['project_value_selectors'] = {'selected_values': selectors}
    with CaptureQueriesContext(connection) as queries:
        statistics = collect_statistics_details(users=False)
    text_column = f'"{Value._meta.db_table}"."text"'
    assert all(text_column not in query['sql'] for query in queries)
    assert all(row['selected_values'] in (None, '') for row in statistics['projects'])
    assert next(row for row in statistics['projects'] if row['project_values'])['project_values'] == 4


def test_rows_are_shuffled_without_exporting_identifiers(inventory, monkeypatch):
    generators = iter([Random(42), Random(1), Random(19), Random(2)])
    monkeypatch.setattr('rdmo_plugins_statistics.exports.utils.SystemRandom', lambda: next(generators))
    first = collect()
    second = collect_statistics_details('rdmo-test', collected_at=COLLECTED_AT)
    for key, columns in (('users', USER_HEADER), ('projects', PROJECT_HEADER)):
        rows = first[key]
        assert len(rows) == len(second[key])
        assert all(row in second[key] for row in rows)
        assert rows != second[key]
        assert all(row['anonymize'] is True for row in rows)
        assert all(set(row) == set(columns.split(',')) for row in rows)
        assert all(not {'user_id', 'project_id', 'random_id'} & row.keys() for row in rows)
    assert [row['user_email_domain'] for row in first['users']] != [
        email_domain(user.email) for user in inventory['people']
    ]


@pytest.mark.parametrize(('instant', 'zone', 'expected'), [
    ('2026-04-15T18:23:45.123456+00:00', 'UTC', '2026-04-15T09:09:09+00:00'),
    ('2026-04-15T08:23:45.123456+00:00', 'Europe/Berlin', '2026-04-15T09:09:09+02:00'),
    ('2026-04-15T20:54:32.654321+00:00', 'Europe/Berlin', '2026-04-15T09:09:09+02:00'),
    ('2025-12-31T23:30:00+00:00', 'Europe/Berlin', '2026-01-01T09:09:09+01:00'),
    ('2026-01-01T00:30:00+00:00', 'America/New_York', '2025-12-31T09:09:09-05:00'),
])
def test_timestamps_keep_the_local_date_with_a_fixed_time(instant, zone, expected):
    value = datetime.fromisoformat(instant)
    tz = ZoneInfo(zone)
    assert anonymize_datetime(value, tz).isoformat() == expected


def test_naive_source_timestamps_use_export_timezone():
    assert anonymize_datetime(datetime(2026, 4, 15, 12, 34, 56), ZoneInfo('Europe/Berlin')).isoformat() == (
        '2026-04-15T09:09:09+02:00'
    )


@pytest.mark.django_db
def test_collection_date_is_not_anonymized_and_uses_one_run_timezone(settings):
    settings.RDMO_STATISTICS_EXPORT = {'timezone': 'America/New_York'}
    statistics = collect_statistics_details('rdmo', collected_at=datetime.fromisoformat('2026-01-01T00:30:00+00:00'))
    assert statistics['metadata']['date'].isoformat() == '2025-12-31'


@pytest.mark.parametrize(('email', 'expected'), [
    ('person@sub.example.co.uk', 'co.uk'),
    ('person@a.b.edu', 'b.edu'),
    ('malformed.example', ''),
    ('person@localhost', 'localhost'),
    ('', ''),
])
def test_email_domain_never_falls_back_to_the_address(email, expected):
    assert email_domain(email) == expected


@pytest.mark.django_db
def test_duplicate_tenant_labels_follow_domain_order():
    Site.objects.all().delete()
    second = Site.objects.create(domain='z.alpha.edu', name='Second')
    Site.objects.create(domain='a.alpha.edu', name='First')
    Site.objects.create(domain='beta.edu', name='Two components')
    assert get_sites_labels() == ['alpha', 'beta.edu', f'alpha_{second.pk}']


@pytest.mark.django_db
def test_command_surfaces_configuration_errors(settings, tmp_path):
    settings.RDMO_STATISTICS_EXPORT = {'timezone': 'Bad/Timezone'}
    with pytest.raises(ZoneInfoNotFoundError):
        call_command('export_statistics_details', server_environment_name='rdmo', output_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_command_surfaces_missing_role_without_exporting_partial_data(inventory, tmp_path):
    inventory['people'][4].role.delete()
    with pytest.raises(Role.DoesNotExist):
        call_command('export_statistics_details', server_environment_name='rdmo', output_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db
@pytest.mark.parametrize('label', ['', ' '])
def test_command_rejects_invalid_source_before_creating_output(label, tmp_path):
    destination = tmp_path / 'not-created'
    with pytest.raises(CommandError, match='--server-environment-name'):
        call_command('export_statistics_details', server_environment_name=label, output_dir=destination)
    assert not destination.exists()


def test_csv_preserves_null_empty_and_literal_text():
    values = [None, '', '\\N', 'NULL', '=SUM(1,2)', '+text', '-text', '@text', '\ttext', '\rtext', 'a,"b"\nc']
    stream = StringIO(newline='')
    csv.writer(stream, quoting=csv.QUOTE_NOTNULL, lineterminator='\n').writerow(format_csv_value(value) for value in values)
    encoded = stream.getvalue()
    assert encoded.startswith(',"","\\N","NULL",')
    assert next(csv.reader(StringIO(encoded))) == ['' if value is None else value for value in values]
    assert format_csv_value(True) == 'true'
    assert format_csv_value(False) == 'false'


@pytest.mark.parametrize('option', ['--no-anonymize', '--include-personal-data', '--fields=username,email'])
def test_command_has_no_personal_data_export_options(option, tmp_path):
    with pytest.raises(CommandError, match='unrecognized arguments'):
        call_command('export_statistics_details', option, '--server-environment-name', 'rdmo', '--output-dir', str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_settings_cannot_disable_anonymization(inventory, settings):
    settings.RDMO_STATISTICS_EXPORT.update({
        'anonymize': False, 'random_id': False, 'fields': ['username', 'email'], 'timestamp_policy': 'raw',
    })
    statistics = collect()
    assert statistics['metadata']['anonymize'] is True
    for table, rows in (('rdmo_users', statistics['users']), ('rdmo_projects', statistics['projects'])):
        for row in rows:
            assert row['anonymize'] is True
            columns = PROJECT_HEADER if table == 'rdmo_projects' else USER_HEADER
            assert set(row) == set(columns.split(','))


def test_writer_always_anonymizes_input_and_excludes_extra_personal_fields(inventory, tmp_path):
    statistics = collect()
    precise = datetime.fromisoformat('2026-10-03T18:42:17.654321+00:00')
    statistics['metadata']['anonymize'] = False
    for key, timestamps in (
        ('users', ('date_joined', 'last_login')),
        ('projects', ('created', 'updated')),
    ):
        for row in statistics[key]:
            row.update({
                'random_id': -999, 'user_id': -999, 'project_id': -999, 'anonymize': False,
                'username': 'PRIVATE_USERNAME', 'email': 'PRIVATE_EMAIL@example.org',
                'first_name': 'PRIVATE_FIRST_NAME', 'last_name': 'PRIVATE_LAST_NAME',
            })
            for field in timestamps:
                if row[field] is not None:
                    row[field] = precise
    completed = export_statistics_details_csv(statistics, tmp_path)
    for table, timestamps in (
        ('rdmo_users', ('date_joined', 'last_login')),
        ('rdmo_projects', ('created', 'updated')),
    ):
        path = completed / f'{table}.csv'
        with path.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            columns = PROJECT_HEADER if table == 'rdmo_projects' else USER_HEADER
            assert reader.fieldnames == columns.split(',')
            rows = list(reader)
        assert len(rows) == len(statistics[table.removeprefix('rdmo_')])
        assert not {'user_id', 'project_id', 'random_id'} & set(reader.fieldnames)
        assert all(row['anonymize'] == 'true' for row in rows)
        for row in rows:
            for field in timestamps:
                if row[field]:
                    assert row[field] == '2026-10-03T09:09:09+02:00'
        assert 'PRIVATE_' not in path.read_text()
    assert json.loads((completed / 'manifest.json').read_text())['anonymize'] is True


@pytest.mark.parametrize('server_environment_name', [None, 'rdmo-test'])
def test_command_publishes_complete_unchanged_text_and_metadata(inventory, tmp_path, server_environment_name):
    stdout = StringIO()
    options = {'server_environment_name': server_environment_name} if server_environment_name else {}
    call_command('export_statistics_details', output_dir=tmp_path, stdout=stdout, **options)
    expected_name = server_environment_name or 'rdmo'
    directories = list(tmp_path.iterdir())
    assert len(directories) == 1
    completed = directories[0]
    assert completed.name.startswith('run-')
    assert str(completed) in stdout.getvalue()
    assert {path.name for path in completed.iterdir()} == {'rdmo_projects.csv', 'rdmo_users.csv', 'manifest.json'}
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert manifest['server_environment_name'] == expected_name
    assert manifest['anonymize'] is True
    assert manifest['database_snapshot'] is False
    assert manifest['schema_version'] == 1
    assert manifest['timestamp_policy'] == 'local-09:09:09'
    assert manifest['timestamp_timezone'] == 'Europe/Berlin'
    for table, header in (('rdmo_projects', PROJECT_HEADER), ('rdmo_users', USER_HEADER)):
        path = completed / f'{table}.csv'
        with path.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == header.split(',')
            rows = list(reader)
        assert manifest['tables'][table]['columns'] == header.split(',')
        assert manifest['tables'][table]['row_count'] == len(rows)
        assert manifest['tables'][table]['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert all(row['date'] == manifest['date'] and row['server_environment_name'] == expected_name for row in rows)
        assert all(row['anonymize'] == 'true' for row in rows)
        assert not {'user_id', 'project_id', 'random_id'} & set(reader.fieldnames)
    with (completed / 'rdmo_projects.csv').open(newline='', encoding='utf-8') as stream:
        root = next(row for row in csv.DictReader(stream) if row['project_values'] == '4')
    assert root['catalog_title_en'] == '=English, "catalog"\nsecond line'
    assert root['selected_values'] == 'Engineering, "physics"\nnext line'
    assert root['progress_total'] == '5'
    assert root['progress_count'] == '3'
    assert 'private-user-' not in (completed / 'rdmo_users.csv').read_text()
    assert 'alice@' not in (completed / 'rdmo_users.csv').read_text()
    assert 'Private project title' not in (completed / 'rdmo_projects.csv').read_text()


@pytest.mark.parametrize(('flags', 'datasets'), [
    ([], {'users', 'projects'}),
    (['--users'], {'users'}),
    (['--projects'], {'projects'}),
    (['--users', '--projects'], {'users', 'projects'}),
])
def test_command_only_queries_and_publishes_selected_datasets(inventory, tmp_path, monkeypatch, flags, datasets):
    def unexpected_collection(*args, **kwargs):
        pytest.fail('Unselected dataset was queried')

    if 'users' not in datasets:
        monkeypatch.setattr('rdmo_plugins_statistics.exports.users.collect_user_details', unexpected_collection)
    if 'projects' not in datasets:
        monkeypatch.setattr('rdmo_plugins_statistics.exports.projects.collect_project_details', unexpected_collection)
    stdout = StringIO()
    call_command(
        'export_statistics_details', *flags, '--server-environment-name', 'rdmo-test',
        '--output-dir', str(tmp_path), stdout=stdout,
    )
    completed, = tmp_path.iterdir()
    tables = {f'rdmo_{key}' for key in datasets}
    assert {path.name for path in completed.iterdir()} == {f'{table}.csv' for table in tables} | {'manifest.json'}
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert set(manifest['tables']) == tables
    for key, count in (('users', 6), ('projects', 4)):
        if key in datasets:
            assert manifest['tables'][f'rdmo_{key}']['row_count'] == count
            assert f'{count} {key}' in stdout.getvalue()
        else:
            assert key not in stdout.getvalue()


@pytest.mark.django_db
def test_empty_export_has_exact_headers_and_explicit_source(tmp_path):
    statistics = collect()
    assert statistics['users'] == statistics['projects'] == []
    completed = export_statistics_details_csv(statistics, tmp_path)
    assert (completed / 'rdmo_projects.csv').read_text() == BASE_PROJECT_HEADER + '\n'
    assert (completed / 'rdmo_users.csv').read_text() == USER_HEADER + '\n'
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert manifest['server_environment_name'] == 'rdmo-test'
    assert manifest['date'] == '2026-10-16'
    assert manifest['tables']['rdmo_projects']['row_count'] == manifest['tables']['rdmo_users']['row_count'] == 0


@pytest.mark.parametrize('failure_stage', ['second_csv', 'manifest', 'rename'])
def test_failed_publication_keeps_previous_runs_and_removes_staging(inventory, tmp_path, monkeypatch, failure_stage):
    statistics = collect()
    previous = export_statistics_details_csv(statistics, tmp_path)
    previous_bytes = {path.name: path.read_bytes() for path in previous.iterdir()}
    original_open = Path.open
    original_write = Path.write_text

    def fail_open(path, *args, **kwargs):
        if failure_stage == 'second_csv' and path.name == 'rdmo_users.csv' and args and args[0] == 'w':
            raise OSError('simulated write failure')
        return original_open(path, *args, **kwargs)

    def fail_manifest(path, *args, **kwargs):
        if failure_stage == 'manifest' and path.name == 'manifest.json':
            raise OSError('simulated write failure')
        return original_write(path, *args, **kwargs)

    def fail_rename(*args, **kwargs):
        raise OSError('simulated write failure')

    monkeypatch.setattr(Path, 'open', fail_open)
    monkeypatch.setattr(Path, 'write_text', fail_manifest)
    if failure_stage == 'rename':
        monkeypatch.setattr(Path, 'rename', fail_rename)
    with pytest.raises(OSError, match='simulated'):
        export_statistics_details_csv(statistics, tmp_path)
    assert list(tmp_path.iterdir()) == [previous]
    assert {path.name: path.read_bytes() for path in previous.iterdir()} == previous_bytes


def test_missing_columns_and_collection_errors_never_publish_partial_rows(inventory, tmp_path, monkeypatch):
    statistics = collect()
    del statistics['users'][0]['last_login']
    with pytest.raises(KeyError, match='last_login'):
        export_statistics_details_csv(statistics, tmp_path)
    assert list(tmp_path.iterdir()) == []
    from rdmo_plugins_statistics.management.commands import export_statistics_details as command

    error = RuntimeError('simulated collection failure')

    def fail_collection(*args, **kwargs):
        raise error

    monkeypatch.setattr(command, 'collect_statistics_details', fail_collection)
    with pytest.raises(RuntimeError, match='simulated collection failure') as exc_info:
        call_command('export_statistics_details', server_environment_name='rdmo', output_dir=tmp_path)
    assert exc_info.value is error
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db
def test_collectors_bound_queries_per_batch_and_only_read():
    owner = get_user_model().objects.create_user(username='owner', email='owner@example.org')
    config = {'timezone': ZoneInfo('UTC'), 'batch_size': 20, 'project_value_selectors': {}}
    metadata = {'date': COLLECTED_AT.date(), 'server_environment_name': 'rdmo', 'anonymize': True}

    def add_project(index):
        project = Project.objects.create(title=f'Project {index}')
        Membership.objects.create(project=project, user=owner, role='owner')

    add_project(0)
    with CaptureQueriesContext(connection) as initial_users:
        collect_user_details(config, metadata)
    with CaptureQueriesContext(connection) as initial_projects:
        collect_project_details(config, metadata)
    for index in range(1, 12):
        get_user_model().objects.create_user(username=f'user-{index}')
        add_project(index)
    with CaptureQueriesContext(connection) as many_users:
        rows = collect_user_details(config, metadata)
    with CaptureQueriesContext(connection) as many_projects:
        projects = collect_project_details(config, metadata)
    assert len(rows) == len(projects) == 12
    assert len(many_users) == len(initial_users) <= 6
    assert len(many_projects) == len(initial_projects) <= 7
    assert all(query['sql'].lstrip().upper().startswith('SELECT') for query in [*many_users, *many_projects])
    assert all(
        f'"{field}"' not in query['sql']
        for field in ('password', 'username', 'first_name', 'last_name')
        for query in [*many_users, *many_projects]
    )
    config['batch_size'] = 5
    with CaptureQueriesContext(connection) as batched:
        assert len(collect_project_details(config, metadata)) == 12
    assert len(batched) <= 3 * 7
