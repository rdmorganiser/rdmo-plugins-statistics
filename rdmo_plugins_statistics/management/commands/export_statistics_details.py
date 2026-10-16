from django.core.management.base import BaseCommand, CommandError

from rdmo_plugins_statistics.exports import collect_statistics_details, export_statistics_details_csv


class Command(BaseCommand):

    help = 'Export anonymized installation-wide project and account rows into a completed run directory.'

    def add_arguments(self, parser):
        parser.add_argument('--server-environment-name', default='rdmo', help='Source label (default: rdmo).')
        parser.add_argument('--output-dir', required=True, help='Parent directory for immutable completed run directories.')
        parser.add_argument(
            '--users', action='store_true', help='Export accounts; defaults to both datasets if neither flag is given.',
        )
        parser.add_argument(
            '--projects', action='store_true', help='Export projects; defaults to both datasets if neither flag is given.',
        )

    def handle(self, *args, **options):
        if not options['server_environment_name'].strip():
            raise CommandError('--server-environment-name must not be empty.')

        statistics = collect_statistics_details(
            options['server_environment_name'],
            users=options['users'] or not options['projects'],
            projects=options['projects'] or not options['users'],
        )
        destination = export_statistics_details_csv(statistics, options['output_dir'])
        counts = ' and '.join(f'{len(statistics[key])} {key}' for key in ('projects', 'users') if key in statistics)
        self.stdout.write(f'Exported {counts} to {destination}.')
