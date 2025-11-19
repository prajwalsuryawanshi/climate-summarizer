from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from weather.models import ClimateRecord, Parameter, Region
from weather.services import metoffice


class MetOfficeParserTests(TestCase):
    def setUp(self):
        self.region = Region.objects.get(code="UK")
        self.parameter = Parameter.objects.get(code="Tmax")

    def _sample_text(self) -> str:
        return (Path(settings.BASE_DIR) / "sample.txt").read_text()

    def test_parse_sample_dataset(self):
        dataframe, last_updated = metoffice.parse_dataset(self._sample_text())
        self.assertGreater(len(dataframe), 0)
        subset = dataframe[dataframe["year"] == 2024]
        records = metoffice.build_records_from_dataframe(
            subset, self.region, self.parameter, last_updated
        )
        self.assertTrue(any(record.period == "ann" for record in records))


class MetOfficeSyncTests(TestCase):
    def setUp(self):
        self.region = Region.objects.get(code="UK")
        self.parameter = Parameter.objects.get(code="Tmax")

    @mock.patch("weather.services.metoffice.fetch_dataset_text")
    def test_sync_uses_bulk_create(self, fetch_dataset_mock):
        fetch_dataset_mock.return_value = (Path(settings.BASE_DIR) / "sample.txt").read_text(), "test-url"
        result = metoffice.sync_dataset(self.region, self.parameter)
        self.assertGreater(result["rows"], 0)
        self.assertTrue(
            ClimateRecord.objects.filter(
                region=self.region, parameter=self.parameter, year=2024, period="ann"
            ).exists()
        )


class ClimateRecordAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.region = Region.objects.get(code="UK")
        self.parameter = Parameter.objects.get(code="Rainfall")
        ClimateRecord.objects.bulk_create(
            [
                ClimateRecord(
                    region=self.region,
                    parameter=self.parameter,
                    year=2020,
                    period_type=ClimateRecord.PeriodType.ANNUAL,
                    period="ann",
                    value=Decimal("100.50"),
                    fetched_at=timezone.now(),
                ),
                ClimateRecord(
                    region=self.region,
                    parameter=self.parameter,
                    year=2021,
                    period_type=ClimateRecord.PeriodType.ANNUAL,
                    period="ann",
                    value=Decimal("120.75"),
                    fetched_at=timezone.now(),
                ),
            ]
        )

    def test_records_endpoint_filters_by_region(self):
        url = reverse("weather:records-list")
        response = self.client.get(
            url,
            {"region": self.region.code, "parameter": self.parameter.code, "period_type": "annual", "limit": 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_summary_endpoint_returns_stats(self):
        url = reverse("weather:records-summary")
        response = self.client.get(
            url,
            {"region": self.region.code, "parameter": self.parameter.code, "period_type": "annual"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertAlmostEqual(response.data["avg_value"], 110.625)


class DatasetIngestAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @mock.patch("weather.services.metoffice.sync_dataset_from_url")
    def test_ingest_endpoint_accepts_url(self, sync_mock):
        sync_mock.return_value = {
            "region": "UK",
            "parameter": "Tmax",
            "rows": 100,
            "source_url": "https://example.com/Tmax/date/UK.txt",
            "last_updated": None,
        }
        url = reverse("weather:ingest")
        payload = {"url": "https://example.com/Tmax/date/UK.txt"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 202)
        sync_mock.assert_called_once_with(payload["url"])

    @mock.patch("weather.services.metoffice.sync_dataset_from_url")
    def test_ingest_endpoint_handles_errors(self, sync_mock):
        sync_mock.side_effect = metoffice.MetOfficeDatasetError("bad url")
        url = reverse("weather:ingest")
        response = self.client.post(url, {"url": "https://bad.example.com/data.txt"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
