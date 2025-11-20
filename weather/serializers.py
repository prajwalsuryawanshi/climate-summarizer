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


class IngestTriggerSerializer(serializers.Serializer):
    regions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    parameters = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique

    def _resolve_codes(self, model, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        missing: list[str] = []
        for value in values:
            try:
                obj = model.objects.get(code__iexact=value)
            except model.DoesNotExist:
                missing.append(value)
            else:
                cleaned.append(obj.code)
        if missing:
            raise serializers.ValidationError(
                f"Unknown {model.__name__.lower()} codes: {', '.join(missing)}"
            )
        return self._dedupe(cleaned)

    def validate_regions(self, values: list[str]) -> list[str]:
        return self._resolve_codes(Region, values)

    def validate_parameters(self, values: list[str]) -> list[str]:
        return self._resolve_codes(Parameter, values)
