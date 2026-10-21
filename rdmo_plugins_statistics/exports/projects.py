"""Anonymized installation-wide project statistics."""

from collections import Counter
from itertools import islice

from django.db.models import Count, Prefetch

from rdmo.core.utils import get_languages
from rdmo.projects.models import Membership, Project, Snapshot, Value

from .project_values import collect_project_values
from .utils import anonymize_datetime, email_domain, join_domains, randomize_rows


def user_domains(user):
    return {site.domain for site in user.role.member.all()} | {site.domain for site in user.role.manager.all()}


def grouped_counts(queryset, field):
    return dict(queryset.order_by().values(field).annotate(count=Count('pk')).values_list(field, 'count'))


def collect_project_details(config, metadata):
    language_fields = {code: f'title_{field}' for code, _, field in get_languages()}
    memberships = (
        Membership.objects.select_related('user__role')
        .only('project_id', 'role', 'user__email', 'user__role')
        .prefetch_related('user__role__member', 'user__role__manager').order_by('pk')
    )
    projects = (
        Project.objects.select_related('site', 'catalog')
        .prefetch_related(Prefetch('memberships', queryset=memberships, to_attr='detail_memberships'))
        .order_by('pk').iterator(chunk_size=config['batch_size'])
    )
    rows = []
    while batch := list(islice(projects, config['batch_size'])):
        ids = {project.pk for project in batch}
        snapshots = grouped_counts(Snapshot.objects.filter(project_id__in=ids), 'project_id')
        children = grouped_counts(Project.objects.filter(parent_id__in=ids), 'parent_id')
        current_values = Value.objects.filter(project_id__in=ids, snapshot__isnull=True)
        value_counts = grouped_counts(current_values, 'project_id')
        titles = {
            project.pk: {
                language: getattr(project.catalog, language_fields[language])
                if project.catalog_id is not None and language in language_fields else ''
                for language in ('de', 'en')
            }
            for project in batch
        }
        selected_values = collect_project_values(batch, config['project_value_selectors'])
        for project in batch:
            members = project.detail_memberships
            counts = Counter(member.role for member in members)
            owner_domains = set()
            collaboration_domains = set()
            for member in members:
                domains = user_domains(member.user)
                collaboration_domains.update(domains)
                if member.role == 'owner':
                    owner_domains.update(domains)
            project_values = value_counts.get(project.pk, 0) if project.catalog_id is not None else 0
            rows.append({
                **selected_values[project.pk],
                **metadata,
                'catalog_id': project.catalog_id,
                'catalog_uri': project.catalog.uri if project.catalog_id is not None else '',
                'catalog_title_de': titles[project.pk]['de'],
                'catalog_title_en': titles[project.pk]['en'],
                'site_id': project.site_id,
                'site_domain': project.site.domain if project.site_id is not None else None,
                'owners_domains': join_domains(owner_domains),
                'project_owners': counts['owner'],
                'project_managers': counts['manager'],
                'project_authors': counts['author'],
                'project_guests': counts['guest'],
                'snapshots': snapshots.get(project.pk, 0),
                'test_project': 'test' in project.title.lower() or 'test' in project.description.lower(),
                'child_projects': children.get(project.pk, 0),
                'empty_project': project_values == 0,
                'project_values': project_values,
                'progress_total': project.progress_total,
                'progress_count': project.progress_count,
                'collaboration_emails_domain': join_domains(
                    email_domain(member.user.email) for member in members
                ),
                'collaboration_site_domain': join_domains(collaboration_domains),
                'created': anonymize_datetime(project.created, config['timezone']),
                'updated': anonymize_datetime(project.updated, config['timezone']),
            })
    return randomize_rows(rows)
