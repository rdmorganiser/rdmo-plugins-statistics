import json
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO

import pytest

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command

from rdmo.conditions.models import Condition
from rdmo.domain.models import Attribute
from rdmo.options.models import Option, OptionSet
from rdmo.projects.models import Project
from rdmo.projects.progress import compute_progress
from rdmo.questions.models import Catalog, Page, Question, QuestionSet, Section

from model_bakery import baker

from tests.helpers import create_test_projects

pytestmark = pytest.mark.django_db


@pytest.fixture
def fixture_catalog():
    site = Site.objects.get_current()
    owner = get_user_model().objects.create_user(username='fixture-owner')
    catalog = baker.make(Catalog, uri_prefix='https://example.org', uri_path='catalog', available=True)
    catalog.sites.add(site)
    section = baker.make(Section, uri_prefix='https://example.org', uri_path='section')
    page = baker.make(Page, uri_prefix='https://example.org', uri_path='page', attribute=None, is_collection=False)
    catalog.sections.add(section)
    section.pages.add(page)
    return site, owner, catalog, page


def question(parent, name, kind='text', **kwargs):
    attribute = baker.make(Attribute, uri_prefix='https://example.org', key=name, parent=None)
    item = baker.make(
        Question, uri_prefix='https://example.org', uri_path=name, attribute=attribute,
        value_type=kind, widget_type='text', is_collection=False, is_optional=False,
        minimum=None, maximum=None, step=None, **kwargs,
    )
    parent.questions.add(item)
    return item


def test_projects_memberships_dates_and_progress(fixture_catalog):
    site, owner, catalog, page = fixture_catalog
    question(page, 'text')
    question(page, 'boolean', 'boolean')
    guest = get_user_model().objects.create_user(username='fixture-guest')
    date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    reports = create_test_projects(
        catalog=catalog, site=site, owners=[owner], members=[(guest, 'guest')], count=2,
        answer_fraction=1, collection_size=1, created_between=(date, date),
    )
    assert len(reports) == 2
    for report in reports:
        project = Project.objects.get(pk=report['project_id'])
        assert project.catalog_id == catalog.pk and project.site_id == site.pk
        assert project.created == date
        assert set(project.memberships.values_list('user_id', 'role')) == {(owner.pk, 'owner'), (guest.pk, 'guest')}
        assert compute_progress(project) == (2, 2)
        assert (project.progress_count, project.progress_total) == (2, 2)
        assert project.values.filter(snapshot=None).count() == 2


def test_nested_collections_and_conditions(fixture_catalog):
    site, owner, catalog, page = fixture_catalog
    trigger = question(page, 'trigger')
    nested = baker.make(QuestionSet, uri_prefix='https://example.org', uri_path='nested', is_collection=True, attribute=None)
    page.questionsets.add(nested)
    answer = question(nested, 'nested-answer')
    answer.is_collection = True
    answer.save()
    condition = baker.make(
        Condition, uri_prefix='https://example.org', uri_path='condition', source=trigger.attribute,
        relation='eq', target_text='show', target_option=None,
    )
    nested.conditions.add(condition)
    reports = create_test_projects(
        catalog=catalog, site=site, owners=[owner], count=1, answer_fraction=1,
        collection_size=2, answer_overrides={trigger.uri: {'text': 'show'}},
    )
    project = Project.objects.get(pk=reports[0]['project_id'])
    assert set(project.values.filter(attribute=answer.attribute).values_list(
        'set_prefix', 'set_index', 'collection_index', 'set_collection'
    )) == {('0', i, j, True) for i in range(2) for j in range(2)}
    assert compute_progress(project) == (3, 3)


def test_skips_and_reproducibility(fixture_catalog):
    site, owner, catalog, page = fixture_catalog
    question(page, 'text')
    file_question = question(page, 'file', 'file')
    outputs = []
    for label in ('one', 'two'):
        report = create_test_projects(
            catalog=catalog, site=site, owners=[owner], count=1, batch_label=label,
            answer_fraction=1, seed=7,
        )[0]
        assert file_question.uri in report['skipped']
        outputs.append(list(Project.objects.get(pk=report['project_id']).values.values_list('text', flat=True)))
    assert outputs[0] == outputs[1]
    with pytest.raises(ValueError, match='already exists'):
        create_test_projects(catalog=catalog, site=site, owners=[owner], batch_label='one')
    assert Project.objects.count() == 2


def test_command_and_validation(fixture_catalog):
    site, owner, catalog, page = fixture_catalog
    question(page, 'text')
    out = StringIO()
    with redirect_stdout(out):
        call_command(
            'runscript',
            'tests.scripts.bake_test_projects',
            script_args=[
                f'--catalog-id {catalog.pk} --owner {owner.username} '
                '--count 1 --batch-label command --answer-fraction 0 0'
            ],
        )
    report = json.loads(out.getvalue())[0]
    assert report['value_count'] == 0
    assert report['progress_total'] == 1
    with pytest.raises(ValueError, match='Unknown question'):
        create_test_projects(catalog=catalog, site=site, owners=[owner], answer_overrides={'missing': {}})
    assert Project.objects.count() == 1


def test_numeric_static_options_and_hidden_question(fixture_catalog):
    site, owner, catalog, page = fixture_catalog
    number = question(page, 'number', 'float')
    number.minimum, number.maximum, number.step = 2, 3, 0.25
    number.save()
    choice = question(page, 'choice', 'option')
    optionset = baker.make(OptionSet, uri_prefix='https://example.org', uri_path='choices', provider_key='')
    option = baker.make(Option, uri_prefix='https://example.org', uri_path='only-option', additional_input='')
    optionset.options.add(option)
    choice.optionsets.add(optionset)
    hidden = question(page, 'hidden')
    hidden.conditions.add(baker.make(
        Condition, uri_prefix='https://example.org', uri_path='never', source=number.attribute,
        relation='eq', target_text='999', target_option=None,
    ))
    report = create_test_projects(catalog=catalog, site=site, owners=[owner], count=1, answer_fraction=1)[0]
    project = Project.objects.get(pk=report['project_id'])
    assert float(project.values.get(attribute=number.attribute).text) in {2, 2.25, 2.5, 2.75, 3}
    assert project.values.get(attribute=choice.attribute).option == option
    assert not project.values.filter(attribute=hidden.attribute).exists()
    assert hidden.uri in report['skipped']
    assert compute_progress(project) == (2, 2)
