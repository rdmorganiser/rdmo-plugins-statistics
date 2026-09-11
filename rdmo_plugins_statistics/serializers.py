from rest_framework import serializers


class ProjectStatisticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    created = serializers.ListField(child=serializers.DictField())
    progress = serializers.ListField(child=serializers.DictField())


class UserStatisticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    registered = serializers.ListField(child=serializers.DictField())


class CatalogStatisticsSerializer(serializers.Serializer):
    usage = serializers.ListField(child=serializers.DictField())


class StatisticsSerializer(serializers.Serializer):
    projects = ProjectStatisticsSerializer()
    users = UserStatisticsSerializer()
    catalogs = CatalogStatisticsSerializer()
