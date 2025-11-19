from django.core.management.base import BaseCommand, CommandError

from weather.models import Parameter, Region
from weather.services.metoffice import MetOfficeDatasetError, sync_dataset


class Command(BaseCommand):
    help = "Fetch summarised Met Office datasets and persist them locally."

    def add_arguments(self, parser):
        parser.add_argument(
            "--regions",
            nargs="+",
            help="Region codes to ingest (default: all regions).",
        )
        parser.add_argument(
            "--parameters",
            nargs="+",
            help="Parameter codes to ingest (default: all parameters).",
        )

    def handle(self, *args, **options):
        regions = Region.objects.all()
        if options.get("regions"):
            filters = [code.upper() for code in options["regions"]]
            regions = regions.filter(code__in=filters)
            if not regions.exists():
                raise CommandError("No matching regions for the supplied codes.")

        parameters = Parameter.objects.all()
        if options.get("parameters"):
            filters = [code for code in options["parameters"]]
            parameters = parameters.filter(code__in=filters)
            if not parameters.exists():
                raise CommandError("No matching parameters for the supplied codes.")

        total_rows = 0
        for region in regions:
            for parameter in parameters:
                self.stdout.write(f"→ Syncing {region.code}/{parameter.code} ...")
                try:
                    result = sync_dataset(region, parameter)
                except MetOfficeDatasetError as exc:
                    self.stderr.write(self.style.ERROR(str(exc)))
                    continue
                total_rows += result["rows"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Saved {result['rows']} rows "
                        f"(last updated {result['last_updated']})"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Completed! {total_rows} rows processed."))

