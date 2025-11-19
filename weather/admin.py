from django.contrib import admin

from .models import ClimateRecord, Parameter, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "dataset_slug")
    search_fields = ("code", "name", "dataset_slug")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "units")
    search_fields = ("code", "name")


@admin.register(ClimateRecord)
class ClimateRecordAdmin(admin.ModelAdmin):
    list_display = ("region", "parameter", "year", "period_type", "period", "value")
    list_filter = ("period_type", "region", "parameter")
    search_fields = ("region__code", "parameter__code", "year", "period")
