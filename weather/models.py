from django.db import models
from django.utils import timezone


class Region(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    dataset_slug = models.CharField(max_length=128, help_text="Slug used in Met Office dataset URLs")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Parameter(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    units = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ClimateRecordQuerySet(models.QuerySet):
    def for_period(self, period_type: str | None = None, period: str | None = None):
        qs = self
        if period_type:
            qs = qs.filter(period_type=period_type)
        if period:
            qs = qs.filter(period=period.lower())
        return qs

    def between_years(self, start_year: int | None = None, end_year: int | None = None):
        qs = self
        if start_year:
            qs = qs.filter(year__gte=start_year)
        if end_year:
            qs = qs.filter(year__lte=end_year)
        return qs


class ClimateRecord(models.Model):
    class PeriodType(models.TextChoices):
        MONTH = "month", "Month"
        SEASON = "season", "Season"
        ANNUAL = "annual", "Annual"

    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="records")
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name="records")
    year = models.PositiveIntegerField()
    period_type = models.CharField(max_length=12, choices=PeriodType.choices)
    period = models.CharField(max_length=12, help_text="Month short name, season code (win/spr/sum/aut) or 'ann'")
    value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    source_last_updated = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(default=timezone.now)

    objects = ClimateRecordQuerySet.as_manager()

    class Meta:
        unique_together = ("region", "parameter", "year", "period_type", "period")
        ordering = ["parameter", "region", "year", "period"]

    def __str__(self) -> str:
        return f"{self.region.code} {self.parameter.code} {self.year} {self.period}"
