from django.db.models import Avg, Max, Min
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ClimateRecordFilter
from .models import ClimateRecord, Parameter, Region
from .serializers import (
    ClimateRecordSerializer,
    IngestRequestSerializer,
    ParameterSerializer,
    RegionSerializer,
)
from .services import metoffice


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    lookup_field = "code"


class ParameterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    lookup_field = "code"


class ClimateRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClimateRecordSerializer
    filterset_class = ClimateRecordFilter
    ordering_fields = ["year", "period", "value", "fetched_at"]
    ordering = ["year", "period"]

    def get_queryset(self):
        return (
            ClimateRecord.objects.select_related("region", "parameter")
            .exclude(value__isnull=True)
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        count = queryset.count()
        if count == 0:
            return Response({"count": 0})

        aggregates = queryset.aggregate(
            min_value=Min("value"),
            max_value=Max("value"),
            avg_value=Avg("value"),
            first_year=Min("year"),
            last_year=Max("year"),
        )

        def _convert(value):
            return None if value is None else float(value)

        payload = {
            "count": count,
            "min_value": _convert(aggregates["min_value"]),
            "max_value": _convert(aggregates["max_value"]),
            "avg_value": _convert(aggregates["avg_value"]),
            "first_year": aggregates["first_year"],
            "last_year": aggregates["last_year"],
            "region": request.query_params.get("region"),
            "parameter": request.query_params.get("parameter"),
            "period_type": request.query_params.get("period_type"),
            "period": request.query_params.get("period"),
        }
        return Response(payload)


class DatasetIngestView(APIView):
    """
    Accepts a Met Office dataset link and ingests it into the local database.
    """

    def post(self, request):
        serializer = IngestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]

        try:
            result = metoffice.sync_dataset_from_url(url)
        except metoffice.MetOfficeDatasetError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Ingestion started successfully.",
                "region": result["region"],
                "parameter": result["parameter"],
                "rows_processed": result["rows"],
                "source_url": result["source_url"],
                "last_updated": result["last_updated"],
            },
            status=status.HTTP_202_ACCEPTED,
        )

