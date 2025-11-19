from __future__ import annotations

import io
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Iterable
from urllib.parse import unquote, urlparse

import pandas as pd
import requests
from django.conf import settings
from django.utils import timezone

from weather.constants import ANNUAL_COLUMN, MONTH_COLUMNS, SEASON_COLUMNS
from weather.models import ClimateRecord, Parameter, Region

logger = logging.getLogger(__name__)


class MetOfficeDatasetError(Exception):
    """Raised when a dataset cannot be fetched or parsed."""


def build_dataset_url(parameter_code: str, dataset_slug: str, order: str = "date") -> str:
    return f"{settings.METOFFICE_BASE_URL}/{parameter_code}/{order}/{dataset_slug}.txt"


def fetch_dataset_text(parameter_code: str, dataset_slug: str) -> tuple[str, str]:
    url = build_dataset_url(parameter_code, dataset_slug)
    return fetch_dataset_text_by_url(url)


def fetch_dataset_text_by_url(url: str) -> tuple[str, str]:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise MetOfficeDatasetError(f"Unable to download dataset {url}") from exc
    return response.text, url


def _parse_last_updated_line(line: str) -> datetime | None:
    try:
        _, value = line.split("Last updated", 1)
    except ValueError:
        return None
    value = value.strip()
    for fmt in ("%d-%b-%Y %H:%M", "%d %B %Y %H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        except ValueError:
            continue
    logger.warning("Failed to parse last updated line: %s", line)
    return None


def parse_dataset(content: str) -> tuple[pd.DataFrame, datetime | None]:
    lines = content.splitlines()
    header_idx = None
    last_updated = None

    for idx, line in enumerate(lines):
        normalised = line.strip().lower()
        if normalised.startswith("last updated"):
            last_updated = _parse_last_updated_line(line)
        if normalised.startswith("year"):
            header_idx = idx
            break

    if header_idx is None:
        raise MetOfficeDatasetError("Could not find dataset header row.")

    data_block = "\n".join(lines[header_idx:])
    dataframe = pd.read_csv(
        io.StringIO(data_block),
        sep=r"\s+",
        na_values=["---", "NA", "na", ""],
    )
    dataframe.columns = [str(col).strip().lower() for col in dataframe.columns]
    return dataframe, last_updated


def _coerce_decimal(value) -> Decimal | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    return Decimal(str(float(value)))


def build_records_from_dataframe(
    dataframe: pd.DataFrame,
    region: Region,
    parameter: Parameter,
    last_updated: datetime | None,
) -> list[ClimateRecord]:
    records: list[ClimateRecord] = []
    fetched_at = timezone.now()

    for _, row in dataframe.iterrows():
        year = int(row["year"])

        def append_record(period_type: str, period: str, value):
            decimal_value = _coerce_decimal(value)
            if decimal_value is None:
                return
            records.append(
                ClimateRecord(
                    region=region,
                    parameter=parameter,
                    year=year,
                    period_type=period_type,
                    period=period.lower(),
                    value=decimal_value,
                    source_last_updated=last_updated,
                    fetched_at=fetched_at,
                )
            )

        for month in MONTH_COLUMNS:
            append_record(ClimateRecord.PeriodType.MONTH, month, row.get(month))

        for season in SEASON_COLUMNS:
            append_record(ClimateRecord.PeriodType.SEASON, season, row.get(season))

        if ANNUAL_COLUMN in row:
            append_record(ClimateRecord.PeriodType.ANNUAL, ANNUAL_COLUMN, row.get(ANNUAL_COLUMN))

    return records


def persist_records(records: Iterable[ClimateRecord]) -> int:
    records = list(records)
    if not records:
        return 0

    ClimateRecord.objects.bulk_create(
        records,
        batch_size=500,
        update_conflicts=True,
        unique_fields=["region", "parameter", "year", "period_type", "period"],
        update_fields=["value", "source_last_updated", "fetched_at"],
    )
    return len(records)


def sync_dataset(region: Region, parameter: Parameter, source_url: str | None = None) -> dict:
    if source_url:
        text, url = fetch_dataset_text_by_url(source_url)
    else:
        text, url = fetch_dataset_text(parameter.code, region.dataset_slug)
    dataframe, last_updated = parse_dataset(text)
    records = build_records_from_dataframe(dataframe, region, parameter, last_updated)
    saved = persist_records(records)
    logger.info(
        "Synced %s/%s -> %s rows",
        region.code,
        parameter.code,
        saved,
    )
    return {
        "region": region.code,
        "parameter": parameter.code,
        "rows": saved,
        "source_url": url,
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


def infer_dataset_identifiers(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise MetOfficeDatasetError("Dataset URL must include scheme and host.")

    path = PurePosixPath(unquote(parsed.path))
    parts = [part for part in path.parts if part not in ("", "/")]
    if len(parts) < 3:
        raise MetOfficeDatasetError("Dataset URL path is not in the expected format.")

    filename = parts[-1]
    if "." not in filename:
        raise MetOfficeDatasetError("Dataset URL must point to a .txt file.")

    dataset_slug = PurePosixPath(filename).stem
    parameter_code = parts[-3]
    return parameter_code, dataset_slug


def resolve_models_from_url(url: str) -> tuple[Region, Parameter]:
    parameter_code, dataset_slug = infer_dataset_identifiers(url)
    try:
        parameter = Parameter.objects.get(code__iexact=parameter_code)
    except Parameter.DoesNotExist as exc:
        raise MetOfficeDatasetError(f"Unknown parameter code '{parameter_code}'.") from exc

    try:
        region = Region.objects.get(dataset_slug__iexact=dataset_slug)
    except Region.DoesNotExist as exc:
        raise MetOfficeDatasetError(f"Unknown region dataset slug '{dataset_slug}'.") from exc

    return region, parameter


def sync_dataset_from_url(url: str) -> dict:
    region, parameter = resolve_models_from_url(url)
    return sync_dataset(region, parameter, source_url=url)

