"""Create reproducible RDMO development fixtures with Model Bakery."""

from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from random import Random

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from rdmo.projects.answers import AnswerTree
from rdmo.projects.models import Membership, Project, Value
from rdmo.projects.progress import compute_progress

from model_bakery import baker


def _range(value, minimum, maximum, name):
    if not isinstance(value, tuple | list):
        value = (value, value)
    if len(value) != 2 or not minimum <= value[0] <= value[1] <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}.')
    return value


def _fraction(value, name):
    if not isinstance(value, int | float) or not 0 <= value <= 1:
        raise ValueError(f'{name} must be between 0 and 1.')
    return value


def _datetime_range(value, name):
    if value is None:
        return None
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise ValueError(f'{name} requires two timezone-aware datetimes.')
    start, end = value
    if not all(isinstance(item, datetime) and item.utcoffset() is not None for item in value) or end < start:
        raise ValueError(f'{name} requires two ordered timezone-aware datetimes.')
    return start, end


@transaction.atomic
def create_test_users(
    *,
    site,
    count=10,
    seed=42,
    batch_label='statistics-users',
    joined_between=None,
    active_fraction=1,
    staff_fraction=0,
    manager_fraction=0,
    editor_fraction=0,
    reviewer_fraction=0,
    last_login_fraction=0.7,
):
    """Create site members with reproducible account flags and registration dates.

    Passwords are deliberately unusable. Role fractions are independent, so a user
    can receive more than one site role. The whole user batch is atomic.
    """
    User = get_user_model()
    if not isinstance(count, int) or count < 1:
        raise ValueError('count must be a positive integer.')
    label = slugify(batch_label)
    if not label:
        raise ValueError('batch_label must contain letters or numbers.')
    fractions = {
        'active': _fraction(active_fraction, 'active_fraction'),
        'staff': _fraction(staff_fraction, 'staff_fraction'),
        'manager': _fraction(manager_fraction, 'manager_fraction'),
        'editor': _fraction(editor_fraction, 'editor_fraction'),
        'reviewer': _fraction(reviewer_fraction, 'reviewer_fraction'),
        'last_login': _fraction(last_login_fraction, 'last_login_fraction'),
    }
    dates = _datetime_range(joined_between, 'joined_between')
    username_field = User._meta.get_field(User.USERNAME_FIELD)
    suffix_length = len(str(count))
    prefix = f'test_{label}_'
    if len(prefix) + suffix_length > username_field.max_length:
        raise ValueError('batch_label is too long for the configured username field.')
    if User.objects.filter(**{f'{User.USERNAME_FIELD}__startswith': prefix}).exists():
        raise ValueError('This user batch label already exists.')

    rng = Random(seed)
    reports = []
    for index in range(1, count + 1):
        username = f'{prefix}{index:0{suffix_length}d}'
        joined = dates[0] + (dates[1] - dates[0]) * rng.random() if dates else None
        fields = {
            User.USERNAME_FIELD: username,
            'is_active': rng.random() < fractions['active'],
            'is_staff': rng.random() < fractions['staff'],
            'is_superuser': False,
        }
        if joined is not None:
            fields['date_joined'] = joined
        if any(field.name == 'email' for field in User._meta.fields):
            fields['email'] = f'{username}@example.invalid'
        if any(field.name == 'first_name' for field in User._meta.fields):
            fields['first_name'] = 'Test'
        if any(field.name == 'last_name' for field in User._meta.fields):
            fields['last_name'] = f'User {index}'
        if joined is not None and rng.random() < fractions['last_login']:
            fields['last_login'] = joined + (dates[1] - joined) * rng.random()
        else:
            fields['last_login'] = None

        user = baker.make(User, **fields)
        user.set_unusable_password()
        user.save(update_fields=['password'])
        user.role.member.add(site)
        roles = ['member']
        for role_name in ('manager', 'editor', 'reviewer'):
            if rng.random() < fractions[role_name]:
                getattr(user.role, role_name).add(site)
                roles.append(role_name)
        reports.append({
            'user_id': user.pk,
            'username': user.get_username(),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'roles': roles,
        })
    return reports


def _visible(element, values, location):
    conditions = list(element.conditions.all())
    return not conditions or any(
        condition.resolve(values, *location) if location else condition.resolve(values)
        for condition in conditions
    )


def _answer(question, rng, values, location, overrides):
    if question.uri in overrides:
        payload = dict(overrides[question.uri])
        if payload.keys() - {'text', 'option', 'external_id'}:
            raise ValueError(f'Unsupported answer override fields for {question.uri}.')
        if payload.get('option') is not None and not question.optionsets.filter(options=payload['option']).exists():
            raise ValueError(f'Option does not belong to {question.uri}.')
        return payload, None

    kind = question.value_type
    if kind == 'option':
        options = []
        for optionset in question.optionsets.all().order_by('pk'):
            if not optionset.provider_key and _visible(optionset, values, location):
                options.extend(optionset.options.order_by('pk'))
        if not options:
            return None, 'No eligible static options; supply an answer override.'
        option = rng.choice(options)
        if option.additional_input:
            return None, 'Selected option needs additional input; supply an answer override.'
        return {'option': option}, None
    if kind in {'integer', 'float'}:
        low = Decimal(str(question.minimum if question.minimum is not None else min(0, question.maximum or 0)))
        high = Decimal(str(question.maximum if question.maximum is not None else max(low, 100)))
        step = Decimal(str(question.step if question.step is not None else 1))
        if not all(x.is_finite() for x in (low, high, step)) or step <= 0 or high < low:
            return None, 'Invalid numeric bounds or step.'
        if kind == 'integer' and (low != low.to_integral() or step != step.to_integral()):
            return None, 'Non-integral integer bounds/step; supply an answer override.'
        steps = int(((high - low) / step).to_integral_value(rounding=ROUND_FLOOR))
        number = low + rng.randint(0, steps) * step
        return {'text': str(number)}, None
    text = {
        'text': f'Test answer {rng.randrange(100000)}',
        'boolean': str(rng.randrange(2)),
        'date': '2026-01-15',
        'datetime': '2026-01-15T12:00:00+00:00',
        'url': 'https://example.org/test',
        'email': 'test@example.org',
        'phone': '+49 30 123456',
    }.get(kind)
    if text is None:
        return None, f'Unsupported value type: {kind}; no files or remote providers are generated.'
    return {'text': text}, None


@transaction.atomic
def fill_project_interview(project, *, seed=42, answer_fraction=1, collection_size=1, answer_overrides=None):
    """Fill an empty interview, retaining hidden answers like the real interview does.

    Overrides map question URIs to Value payloads (text, option, external_id).
    Questions are attempted once per location; hidden questions are revisited.
    """
    fraction = _range(answer_fraction, 0, 1, 'answer_fraction')
    sizes = _range(collection_size, 1, 20, 'collection_size')
    if any(not isinstance(size, int) for size in sizes):
        raise ValueError('collection_size must contain integers.')
    if project.catalog is None or project.values.exists():
        raise ValueError('An empty project with a catalog is required.')
    rng = Random(seed)
    fraction = rng.uniform(*fraction)
    overrides = answer_overrides or {}
    project.catalog.prefetch_elements()
    questions = [e for e in project.catalog.descendants if e._meta.model_name == 'question']
    unknown = overrides.keys() - {q.uri for q in questions}
    if unknown:
        raise ValueError(f'Unknown question override URIs: {sorted(unknown)}')
    attempted, occupied, seen = set(), set(), set()
    set_sizes, skipped = {}, {}

    def visit(element, parent=None, parent_collection=False):
        kind = element._meta.model_name
        values = project.values.filter(snapshot=None)
        if kind in {'page', 'questionset', 'question'} and not _visible(element, values, parent):
            return
        if kind in {'catalog', 'section'}:
            for child in element.elements:
                visit(child)
        elif kind in {'page', 'questionset'}:
            key = (kind, element.pk, parent)
            if key not in set_sizes:
                set_sizes[key] = rng.randint(*sizes) if element.is_collection else 1
            prefix = AnswerTree.compute_child_set_prefix(parent)
            if len(prefix) > Value._meta.get_field('set_prefix').max_length:
                raise ValueError('Catalog nesting exceeds the Value set_prefix limit.')
            for index in range(set_sizes[key]):
                for child in element.elements:
                    visit(child, (prefix, index), element.is_collection)
        elif kind == 'question':
            seen.add(element.uri)
            key = (element.pk, parent)
            if key in attempted:
                return
            attempted.add(key)
            if element.attribute_id is None:
                skipped[element.uri] = 'Question has no attribute.'
                return
            if element.uri not in overrides and rng.random() >= fraction:
                return
            count = rng.randint(*sizes) if element.is_collection else 1
            for index in range(count):
                location = (element.attribute_id, *parent, index)
                if location in occupied:
                    continue
                payload, reason = _answer(element, rng, values, parent, overrides)
                if reason:
                    skipped[element.uri] = reason
                    continue
                baker.make(
                    Value, project=project, snapshot=None, attribute=element.attribute,
                    set_prefix=parent[0], set_index=parent[1], set_collection=parent_collection,
                    collection_index=index, value_type=element.value_type, unit=element.unit,
                    **({'text': '', 'option': None, 'external_id': '', 'file': None} | payload),
                )
                occupied.add(location)

    for _ in range(32):
        before = len(occupied)
        visit(project.catalog)
        if len(occupied) == before:
            break
    else:
        raise ValueError('Conditional interview did not settle within 32 passes.')
    for question in questions:
        if question.uri not in seen:
            skipped[question.uri] = 'Not visible under the generated answers or ancestor collections.'
    project.progress_count, project.progress_total = compute_progress(project)
    project.save(update_fields=['progress_count', 'progress_total'])
    return {
        'project_id': project.pk, 'value_count': len(occupied),
        'progress_count': project.progress_count, 'progress_total': project.progress_total,
        'skipped': skipped,
    }


def create_test_projects(*, catalog, site, owners, members=(), count=10, seed=42,
                         batch_label='statistics-demo', answer_fraction=(0.2, 0.9),
                         collection_size=(1, 3), created_between=None, answer_overrides=None):
    """Create fixtures using existing users/catalog; return one report per project.

    Each project is atomic. Earlier projects remain if a later project fails.
    Repeating a batch label is rejected, preventing accidental duplicate runs.
    """
    owners, members = list(owners), list(members)
    if not isinstance(count, int) or count < 1 or not owners:
        raise ValueError('Supply a positive count and at least one owner.')
    if not batch_label.strip() or len(batch_label) > 180:
        raise ValueError('batch_label must contain 1-180 characters.')
    if not catalog.available or not catalog.sites.filter(pk=site.pk).exists():
        raise ValueError('Catalog must be available and assigned to the selected site.')
    roles = dict(Membership.ROLE_CHOICES)
    if any(role not in roles for _, role in members):
        raise ValueError('Unknown membership role.')
    if len({u.pk for u, _ in members}) != len(members):
        raise ValueError('Supply each additional member only once.')
    if {u.pk for u in owners} & {u.pk for u, _ in members}:
        raise ValueError('Owner pool and additional members must not overlap.')
    for user in [*owners, *(u for u, _ in members)]:
        if not user.pk or not user.role.member.filter(pk=site.pk).exists():
            raise ValueError(f'User {user} must belong to the selected site.')
    _range(answer_fraction, 0, 1, 'answer_fraction')
    _range(collection_size, 1, 20, 'collection_size')
    dates = _datetime_range(created_between, 'created_between')
    prefix = f'[test:{batch_label}] '
    if Project.objects.filter(site=site, title__startswith=prefix).exists():
        raise ValueError('This batch label already exists on the selected site.')
    rng, reports = Random(seed), []
    for index in range(count):
        with transaction.atomic():
            project = baker.make(
                Project, site=site, catalog=catalog, parent=None,
                title=f'{prefix}{index + 1:04d}', description='Generated test project.',
                progress_count=None, progress_total=None,
            )
            baker.make(Membership, project=project, user=owners[index % len(owners)], role='owner')
            for user, role in members:
                baker.make(Membership, project=project, user=user, role=role)
            report = fill_project_interview(
                project, seed=rng.randrange(2**32), answer_fraction=answer_fraction,
                collection_size=collection_size, answer_overrides=answer_overrides,
            )
            if dates:
                start, end = dates
                created = start + (end - start) * rng.random()
                Project.objects.filter(pk=project.pk).update(created=created, updated=created)
                project.values.update(created=created, updated=created)
            reports.append(report)
    return reports
