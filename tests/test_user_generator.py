import json
from datetime import datetime, timezone
from io import StringIO

import pytest

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command

from rdmo_plugins_statistics.testing import create_test_users

pytestmark = pytest.mark.django_db


def test_create_test_users_with_dates_and_roles():
    site = Site.objects.get_current()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, tzinfo=timezone.utc)

    reports = create_test_users(
        site=site,
        count=3,
        seed=7,
        batch_label='dated-users',
        joined_between=(start, end),
        active_fraction=0,
        staff_fraction=1,
        manager_fraction=1,
        editor_fraction=1,
        reviewer_fraction=1,
        last_login_fraction=1,
    )

    users = list(get_user_model().objects.filter(username__startswith='test_dated-users_').order_by('username'))
    assert len(users) == len(reports) == 3
    assert len({user.date_joined for user in users}) == 3
    for user in users:
        assert start <= user.date_joined <= end
        assert user.date_joined <= user.last_login <= end
        assert not user.is_active
        assert user.is_staff
        assert not user.has_usable_password()
        assert user.role.member.filter(pk=site.pk).exists()
        assert user.role.manager.filter(pk=site.pk).exists()
        assert user.role.editor.filter(pk=site.pk).exists()
        assert user.role.reviewer.filter(pk=site.pk).exists()


def test_create_test_users_is_reproducible_and_rejects_duplicate_batch():
    site = Site.objects.get_current()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, tzinfo=timezone.utc)
    first = create_test_users(site=site, count=2, seed=5, batch_label='first', joined_between=(start, end))
    second = create_test_users(site=site, count=2, seed=5, batch_label='second', joined_between=(start, end))

    assert [item['date_joined'] for item in first] == [item['date_joined'] for item in second]
    assert [item['is_active'] for item in first] == [item['is_active'] for item in second]
    with pytest.raises(ValueError, match='already exists'):
        create_test_users(site=site, batch_label='first')
    assert get_user_model().objects.count() == 4


def test_create_statistics_test_users_command():
    out = StringIO()
    call_command(
        'create_statistics_test_users',
        count=2,
        batch_label='command-users',
        active_fraction=0,
        stdout=out,
    )
    reports = json.loads(out.getvalue())
    assert len(reports) == 2
    assert not any(item['is_active'] for item in reports)
    assert all(item['roles'] == ['member'] for item in reports)


@pytest.mark.parametrize('kwargs', [
    {'count': 0},
    {'active_fraction': 2},
    {'joined_between': (datetime.now(), datetime.now())},
    {'batch_label': '***'},
])
def test_create_test_users_validates_input(kwargs):
    with pytest.raises(ValueError):
        create_test_users(site=Site.objects.get_current(), **kwargs)
