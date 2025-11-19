from rest_framework import serializers

from .models import ClimateRecord, Parameter, Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "code", "name", "dataset_slug", "description"]


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ["id", "code", "name", "units", "description"]


class ClimateRecordSerializer(serializers.ModelSerializer):
    region_code = serializers.CharField(source="region.code", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)
    parameter_code = serializers.CharField(source="parameter.code", read_only=True)
    parameter_name = serializers.CharField(source="parameter.name", read_only=True)

    class Meta:
        model = ClimateRecord
        fields = [
            "id",
            "year",
            "period_type",
            "period",
            "value",
            "region_code",
            "region_name",
            "parameter_code",
            "parameter_name",
            "source_last_updated",
            "fetched_at",
        ]


class IngestRequestSerializer(serializers.Serializer):
    url = serializers.URLField()

