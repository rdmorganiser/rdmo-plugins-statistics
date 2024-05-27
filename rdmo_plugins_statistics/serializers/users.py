from collections import Counter
from datetime import datetime
from typing import Optional

from django.contrib.auth import get_user_model

from rest_framework import serializers

from rdmo_plugins_statistics.serializers.utils import get_domain_from_email, get_project_role_count


class AnonymousUserStatisticsSerializer(serializers.ModelSerializer):

    date_joined = serializers.SerializerMethodField()
    date_last_login = serializers.SerializerMethodField()
    member_sites = serializers.SerializerMethodField()
    project_owner_count = serializers.SerializerMethodField()
    project_manager_count = serializers.SerializerMethodField()
    project_author_count = serializers.SerializerMethodField()
    project_guest_count = serializers.SerializerMethodField()
    external_email_domain = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            'date_joined',
            'date_last_login',
            'member_sites',
            'external_email_domain',
            'project_owner_count',
            'project_manager_count',
            'project_author_count',
            'project_guest_count',
        ]

    def get_date_joined(self, user) -> Optional[datetime.date]:
        if user.date_joined is not None:
            return user.date_joined.date()

    def get_date_last_login(self, user) -> Optional[datetime.date]:
        if user.last_login is not None:
            return user.last_login.date()

    def get_member_sites(self, user) -> Optional[str]:
        if not user.role or not user.role.member.exists():
            return None
        return ", ".join(site.domain for site in user.role.member.all())

    def get_project_owner_count(self, user) -> int:
        return get_project_role_count(user, 'owner')

    def get_project_manager_count(self, user) -> int:
        return get_project_role_count(user, 'manager')

    def get_project_author_count(self, user) -> int:
        return get_project_role_count(user, 'author')

    def get_project_guest_count(self, user) -> int:
        return get_project_role_count(user, 'guest')

    def get_external_email_domain(self, user) -> Optional[bool]:
        if not user.email:
            return None
        if not "@" in user.email:
            return None
        email_domain = get_domain_from_email(user.email)
        return not user.role.member.all().filter(domain__contains=email_domain).exists()

