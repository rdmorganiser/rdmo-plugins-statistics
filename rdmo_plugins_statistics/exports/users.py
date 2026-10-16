"""Anonymized installation-wide account statistics."""

from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site

from .utils import anonymize_datetime, email_domain, join_domains, randomize_rows


def get_sites_labels():
    # The sites API follows Site's domain ordering. Use pk to break domain ties.
    labels = []
    for site in Site.objects.order_by('domain', 'pk'):
        parts = site.domain.split('.')
        label = parts[-2] if len(parts) > 2 else site.domain
        if label in labels:
            label = f'{label}_{site.pk}'
        labels.append(label)
    return labels


def collect_user_details(config, metadata):
    sites_labels = get_sites_labels()
    users = (
        get_user_model().objects.select_related('role')
        .only('pk', 'email', 'date_joined', 'last_login', 'role')
        .prefetch_related('role__member', 'memberships')
        .order_by('pk')
    )
    rows = []
    for user in users.iterator(chunk_size=config['batch_size']):
        domain = email_domain(user.email)
        counts = Counter(membership.role for membership in user.memberships.all())
        rows.append({
            **metadata,
            'user_email_domain': domain,
            'user_email_associated_domain': join_domains(label for label in sites_labels if label in domain) or 'other',
            'member': join_domains(site.domain for site in user.role.member.all()),
            'project_owner': counts['owner'],
            'project_manager': counts['manager'],
            'project_author': counts['author'],
            'project_guest': counts['guest'],
            'date_joined': anonymize_datetime(user.date_joined, config['timezone']),
            'last_login': anonymize_datetime(user.last_login, config['timezone']),
        })
    return randomize_rows(rows)
