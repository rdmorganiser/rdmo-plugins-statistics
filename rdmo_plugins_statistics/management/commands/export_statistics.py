from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from rdmo_plugins_statistics.exports import export_statistics_csv
from rdmo_plugins_statistics.statistics import fetch_statistics_for_sites


class Command(BaseCommand):
    help = 'Export the latest per-site statistics into five CSV tables.'

    def add_arguments(self, parser):
        selection = parser.add_mutually_exclusive_group()
        selection.add_argument('--site-id', action='append', type=int)
        selection.add_argument('--all-sites', action='store_true')
        parser.add_argument('--output-dir', required=True)

    def handle(self, *args, **options):
        if options['site_id']:
            site_ids = list(dict.fromkeys(options['site_id']))
            sites_by_id = Site.objects.in_bulk(site_ids)
            missing = set(site_ids) - sites_by_id.keys()
            if missing:
                raise CommandError(f'Unknown site IDs: {sorted(missing)}')
            sites = [sites_by_id[site_id] for site_id in site_ids]
        elif options['all_sites']:
            sites = Site.objects.order_by('pk')
        else:
            sites = [Site.objects.get_current()]

        with timezone.override(settings.TIME_ZONE):
            statistics = fetch_statistics_for_sites(sites)
        try:
            export_statistics_csv(statistics, options['output_dir'])
        except OSError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Exported statistics for {len(statistics)} sites to {options["output_dir"]}.')
