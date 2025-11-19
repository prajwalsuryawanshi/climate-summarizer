import django_filters

from .models import ClimateRecord


class ClimateRecordFilter(django_filters.FilterSet):
    start_year = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    end_year = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    region = django_filters.CharFilter(field_name="region__code", lookup_expr="iexact")
    parameter = django_filters.CharFilter(field_name="parameter__code", lookup_expr="iexact")
    period = django_filters.CharFilter(field_name="period", lookup_expr="iexact")

    class Meta:
        model = ClimateRecord
        fields = ["region", "parameter", "period_type", "period"]

