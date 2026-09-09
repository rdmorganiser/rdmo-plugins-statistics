import json
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from rdmo.questions.models import Catalog

from rdmo_plugins_statistics.testing import create_test_projects


class Command(BaseCommand):
    help = 'Create catalog-based test projects, memberships and interview values.'

    def add_arguments(self, parser):
        parser.add_argument('--catalog-id', type=int, required=True)
        parser.add_argument('--site-id', type=int)
        parser.add_argument('--owner', action='append', required=True, help='Username; repeat for an owner pool.')
        parser.add_argument('--member', action='append', default=[], help='USERNAME:ROLE; repeat for extra members.')
        parser.add_argument('--count', type=int, default=10)
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--batch-label', required=True)
        parser.add_argument('--answer-fraction', type=float, nargs=2, default=(0.2, 0.9), metavar=('MIN', 'MAX'))
        parser.add_argument('--collection-size', type=int, nargs=2, default=(1, 3), metavar=('MIN', 'MAX'))
        parser.add_argument('--created-start', help='ISO datetime with timezone offset.')
        parser.add_argument('--created-end', help='ISO datetime with timezone offset.')

    def handle(self, *args, **options):
        try:
            User = get_user_model()
            site = Site.objects.get(pk=options['site_id']) if options['site_id'] else Site.objects.get_current()
            catalog = Catalog.objects.get(pk=options['catalog_id'])
            owners = [User.objects.get(**{User.USERNAME_FIELD: name}) for name in options['owner']]
            members = []
            for member in options['member']:
                name, role = member.rsplit(':', 1)
                members.append((User.objects.get(**{User.USERNAME_FIELD: name}), role))
            start, end = options['created_start'], options['created_end']
            if bool(start) != bool(end):
                raise ValueError('Supply both --created-start and --created-end.')
            dates = (datetime.fromisoformat(start), datetime.fromisoformat(end)) if start else None
            reports = create_test_projects(
                catalog=catalog, site=site, owners=owners, members=members,
                count=options['count'], seed=options['seed'], batch_label=options['batch_label'],
                answer_fraction=options['answer_fraction'], collection_size=options['collection_size'],
                created_between=dates,
            )
        except (ObjectDoesNotExist, ValueError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(reports, indent=2))
