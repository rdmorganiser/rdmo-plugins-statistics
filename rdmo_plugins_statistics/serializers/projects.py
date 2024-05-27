from django.contrib.sites.models import Site
from rest_framework import serializers
from collections import Counter

from rdmo.accounts.serializers.v1 import SiteSerializer
from rdmo.projects.models.project import Project

from rdmo_plugins_statistics.serializers.utils import get_domain_from_email, project_contains_test

QUESTION_OF_INTEREST_SEARCH_TERM = 'fachbereich'


class ProjectStatisticsSerializer(serializers.ModelSerializer):

    catalog_id = serializers.SerializerMethodField()
    catalog_uri = serializers.SerializerMethodField()
    catalog_title_de = serializers.SerializerMethodField()
    catalog_title_en = serializers.SerializerMethodField()
    project_owners_domains = serializers.SerializerMethodField()
    project_owners_count = serializers.SerializerMethodField()
    project_managers_count = serializers.SerializerMethodField()
    project_authors_count = serializers.SerializerMethodField()
    project_guests_count = serializers.SerializerMethodField()
    snapshots_count = serializers.SerializerMethodField()
    test_project = serializers.SerializerMethodField()
    child_projects = serializers.SerializerMethodField()
    empty_project = serializers.SerializerMethodField()
    project_values_count = serializers.SerializerMethodField()
    memberships_unique_domains_count = serializers.SerializerMethodField()
    subject_area = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    updated_date = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'site_id',
            'site_domain',
            'progress_total',
            'progress_count',
            'catalog_id',
            'catalog_uri',
            'catalog_title_de',
            'catalog_title_en',
            'project_owners_domains',
            'project_owners_count',
            'project_managers_count',
            'project_authors_count',
            'project_guests_count',
            'snapshots_count',
            'test_project',
            'child_projects',
            'empty_project',
            'project_values_count',
            'memberships_unique_domains_count',
            'subject_area',
            'created_date',
            'updated_date'
        ]
    site_domain = serializers.SerializerMethodField()
    def get_site_domain(self, project):
        if project.site:
            return project.site.domain


    def get_catalog_id(self, project) -> int:
        return project.catalog.id if project.catalog else None

    def get_catalog_uri(self, project) -> str:
        return project.catalog.uri if project.catalog else ""

    def get_catalog_title_en(self, project) -> str:
        return project.catalog.title_lang1 if project.catalog else ""

    def get_catalog_title_de(self, project) -> str:
        return project.catalog.title_lang2 if project.catalog else ""

    def get_created_date(self, project):
        return project.created.date()

    def get_updated_date(self, project):
        return project.updated.date()

    def get_project_owners_domains(self, project) -> str:
        project_owners = project.owners.all()
        project_owners_member_sites_domains = set([a.domain
                                                   for i in project.owners
                                                   for a in i.role.member.all() if a is not None])
        return ", ".join(project_owners_member_sites_domains)

    def get_project_owners_count(self, project) -> int:
        return project.owners.count()

    def get_project_managers_count(self, project) -> int:
        return project.managers.count()

    def get_project_authors_count(self, project) -> int:
        return project.authors.count()

    def get_project_guests_count(self, project) -> int:
        return project.guests.count()

    def get_snapshots_count(self, project) -> int:
        return project.snapshots.count() if hasattr(project, 'snapshots') else 0

    def get_test_project(self, project) -> bool:
        return project_contains_test(project)

    def get_child_projects(self, project):
        return project.children.count()

    def get_empty_project(self, project):
        return project.values.count() == 0

    def get_project_values_count(self, project):
        return project.values.count()

    def get_subject_area(self, project):
        values_search = project.values.filter(attribute__uri__endswith=QUESTION_OF_INTEREST_SEARCH_TERM)
        if values_search.exists():
            return values_search.first().option.text_lang1

    def get_memberships_unique_domains_count(self, project) -> int:
        member_mail_domains = [get_domain_from_email(i)
                               for i in project.memberships.all().values_list('user__email', flat=True)]

        return len(set(member_mail_domains))
