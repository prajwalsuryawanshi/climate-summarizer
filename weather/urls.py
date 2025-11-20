from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, views

app_name = "weather"

router = DefaultRouter()
router.register("regions", api.RegionViewSet, basename="regions")
router.register("parameters", api.ParameterViewSet, basename="parameters")
router.register("records", api.ClimateRecordViewSet, basename="records")

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("api/", include(router.urls)),
    path("api/ingest/", api.DatasetIngestView.as_view(), name="ingest"),
    path("api/ingest/trigger/", api.DatasetIngestTriggerView.as_view(), name="ingest-trigger"),
]

