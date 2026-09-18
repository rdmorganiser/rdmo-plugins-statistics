import argparse
import json
import shlex
from datetime import datetime

from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError

from tests.helpers import create_test_users


def get_arguments(args):
    parser = argparse.ArgumentParser(description='Create test users with varied dates and RDMO site roles.')
    parser.add_argument('--site-id', type=int)
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--batch-label', required=True)
    parser.add_argument('--joined-start', help='ISO datetime with timezone offset.')
    parser.add_argument('--joined-end', help='ISO datetime with timezone offset.')
    parser.add_argument('--active-fraction', type=float, default=1)
    parser.add_argument('--staff-fraction', type=float, default=0)
    parser.add_argument('--manager-fraction', type=float, default=0)
    parser.add_argument('--editor-fraction', type=float, default=0)
    parser.add_argument('--reviewer-fraction', type=float, default=0)
    parser.add_argument('--last-login-fraction', type=float, default=0.7)
    return parser.parse_args(shlex.split(' '.join(args)))


def run(*args):
    options = get_arguments(args)
    try:
        site = Site.objects.get(pk=options.site_id) if options.site_id else Site.objects.get_current()
        if bool(options.joined_start) != bool(options.joined_end):
            raise ValueError('Supply both --joined-start and --joined-end.')
        dates = (
            (datetime.fromisoformat(options.joined_start), datetime.fromisoformat(options.joined_end))
            if options.joined_start else None
        )
        reports = create_test_users(
            site=site,
            count=options.count,
            seed=options.seed,
            batch_label=options.batch_label,
            joined_between=dates,
            active_fraction=options.active_fraction,
            staff_fraction=options.staff_fraction,
            manager_fraction=options.manager_fraction,
            editor_fraction=options.editor_fraction,
            reviewer_fraction=options.reviewer_fraction,
            last_login_fraction=options.last_login_fraction,
        )
    except (ObjectDoesNotExist, ValueError) as exc:
        raise CommandError(str(exc)) from exc
    print(json.dumps(reports, indent=2))
