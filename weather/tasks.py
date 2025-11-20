from __future__ import annotations

import logging
from typing import Iterable, Sequence

from celery import shared_task

from weather.models import Parameter, Region
from weather.services import metoffice

logger = logging.getLogger(__name__)


def _dedupe(values: Sequence[str] | None) -> list[str] | None:
    if not values:
        return None
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


@shared_task(bind=True, name="weather.ingest_metoffice")
def ingest_metoffice_task(self, regions: Sequence[str] | None = None, parameters: Sequence[str] | None = None):
    """
    Trigger a Met Office ingestion run optionally scoped by region/parameter codes.
    """

    regions = _dedupe(regions)
    parameters = _dedupe(parameters)

    region_qs = Region.objects.all()
    if regions:
        region_qs = region_qs.filter(code__in=regions)
    parameter_qs = Parameter.objects.all()
    if parameters:
        parameter_qs = parameter_qs.filter(code__in=parameters)

    region_list = list(region_qs)
    parameter_list = list(parameter_qs)

    if not region_list:
        message = "No regions matched the supplied filters." if regions else "No regions available to ingest."
        logger.warning("[ingest-task] %s", message)
        return {"runs": [], "total_rows": 0, "message": message}

    if not parameter_list:
        message = "No parameters matched the supplied filters." if parameters else "No parameters available to ingest."
        logger.warning("[ingest-task] %s", message)
        return {"runs": [], "total_rows": 0, "message": message}

    results: list[dict] = []
    failures: list[dict[str, str]] = []
    total_rows = 0

    for region in region_list:
        for parameter in parameter_list:
            logger.info("[ingest-task] Syncing %s/%s", region.code, parameter.code)
            try:
                result = metoffice.sync_dataset(region, parameter)
            except metoffice.MetOfficeDatasetError as exc:
                logger.exception(
                    "[ingest-task] Failed to ingest %s/%s: %s", region.code, parameter.code, exc
                )
                failures.append({"region": region.code, "parameter": parameter.code, "error": str(exc)})
                continue
            total_rows += result["rows"]
            results.append(result)

    payload = {
        "task_id": getattr(self.request, "id", None),
        "regions": [region.code for region in region_list],
        "parameters": [parameter.code for parameter in parameter_list],
        "runs": results,
        "failures": failures,
        "total_rows": total_rows,
    }
    logger.info(
        "[ingest-task] Completed ingestion (task_id=%s total_rows=%s)",
        payload["task_id"],
        total_rows,
    )
    return payload

