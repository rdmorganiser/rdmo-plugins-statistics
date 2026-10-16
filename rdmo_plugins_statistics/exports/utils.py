"""Shared export settings and mandatory anonymization helpers."""

from random import SystemRandom
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def get_detail_settings():
    config = getattr(settings, 'RDMO_STATISTICS_EXPORT', {})
    return {
        'timezone': ZoneInfo(config.get('timezone', settings.TIME_ZONE)),
        'batch_size': config.get('batch_size', 500),
        'project_value_selectors': config.get('project_value_selectors', {}),
    }


def anonymize_datetime(value, tz):
    """Keep the calendar date in the export timezone and use a fixed time."""
    if value is None:
        return None
    local = timezone.make_aware(value, tz) if timezone.is_naive(value) else timezone.localtime(value, tz)
    return local.replace(hour=9, minute=9, second=9, microsecond=0)


def email_domain(email):
    if '@' not in email:
        return ''
    return '.'.join(email.split('@')[-1].split('.')[-2:])


def join_domains(domains):
    return ', '.join(sorted(set(domains)))


def randomize_rows(rows):
    """Shuffle rows and enforce the mandatory anonymization flag."""
    for row in rows:
        row['anonymize'] = True
    SystemRandom().shuffle(rows)
    return rows
