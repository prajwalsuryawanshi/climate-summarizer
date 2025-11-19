from django.db import migrations


REGIONS = [
    {"code": "UK", "name": "United Kingdom", "dataset_slug": "UK"},
    {"code": "ENGLAND", "name": "England", "dataset_slug": "England"},
    {"code": "WALES", "name": "Wales", "dataset_slug": "Wales"},
    {"code": "SCOTLAND", "name": "Scotland", "dataset_slug": "Scotland"},
    {"code": "NORTHERN_IRELAND", "name": "Northern Ireland", "dataset_slug": "Northern_Ireland"},
    {"code": "ENGLAND_WALES", "name": "England & Wales", "dataset_slug": "England_and_Wales"},
    {"code": "ENGLAND_N", "name": "England N", "dataset_slug": "England_N"},
    {"code": "ENGLAND_S", "name": "England S", "dataset_slug": "England_S"},
    {"code": "SCOTLAND_N", "name": "Scotland N", "dataset_slug": "Scotland_N"},
    {"code": "SCOTLAND_E", "name": "Scotland E", "dataset_slug": "Scotland_E"},
    {"code": "SCOTLAND_W", "name": "Scotland W", "dataset_slug": "Scotland_W"},
    {"code": "ENGLAND_E_NE", "name": "England E & NE", "dataset_slug": "England_E_and_NE"},
    {"code": "ENGLAND_NW_WALES_N", "name": "England NW / Wales N", "dataset_slug": "England_NW_and_N_Wales"},
    {"code": "MIDLANDS", "name": "Midlands", "dataset_slug": "Midlands"},
    {"code": "EAST_ANGLIA", "name": "East Anglia", "dataset_slug": "East_Anglia"},
    {"code": "ENGLAND_SW_WALES_S", "name": "England SW / Wales S", "dataset_slug": "England_SW_and_S_Wales"},
    {"code": "ENGLAND_SE_CENTRAL_S", "name": "England SE / Central S", "dataset_slug": "England_SE_and_Central_S"},
]

PARAMETERS = [
    {
        "code": "Tmax",
        "name": "Mean daily maximum temperature",
        "units": "°C",
        "description": "Monthly, seasonal and annual mean of daily maximum air temperature.",
    },
    {
        "code": "Tmin",
        "name": "Mean daily minimum temperature",
        "units": "°C",
        "description": "Monthly, seasonal and annual mean of daily minimum air temperature.",
    },
    {
        "code": "Tmean",
        "name": "Mean temperature",
        "units": "°C",
        "description": "Monthly, seasonal and annual mean air temperature.",
    },
    {
        "code": "Rainfall",
        "name": "Rainfall",
        "units": "mm",
        "description": "Monthly, seasonal and annual total rainfall.",
    },
    {
        "code": "Raindays1mm",
        "name": "Rain days (≥1mm)",
        "units": "days",
        "description": "Number of days each month/season/annum with ≥1mm of rainfall.",
    },
    {
        "code": "Sunshine",
        "name": "Sunshine duration",
        "units": "hours",
        "description": "Monthly, seasonal and annual total duration of bright sunshine.",
    },
    {
        "code": "AirFrost",
        "name": "Air frost days",
        "units": "days",
        "description": "Number of days with air frost.",
    },
]


def seed_reference_data(apps, schema_editor):
    Region = apps.get_model("weather", "Region")
    Parameter = apps.get_model("weather", "Parameter")

    for region in REGIONS:
        Region.objects.update_or_create(code=region["code"], defaults=region)

    for parameter in PARAMETERS:
        Parameter.objects.update_or_create(code=parameter["code"], defaults=parameter)


def reverse_seed(apps, schema_editor):
    Region = apps.get_model("weather", "Region")
    Parameter = apps.get_model("weather", "Parameter")
    Region.objects.filter(code__in=[region["code"] for region in REGIONS]).delete()
    Parameter.objects.filter(code__in=[parameter["code"] for parameter in PARAMETERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('weather', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_reference_data, reverse_seed),
    ]

