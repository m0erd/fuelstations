import csv
from django.core.management.base import BaseCommand
from api.models import FuelStation


class Command(BaseCommand):
    help = "Load fuel stations from CSV quickly (no geocoding)"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_path']
        stations_to_create = []
        seen = set()

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row["Truckstop Name"].strip()
                city = row["City"].strip()
                state = row["State"].strip()
                address = f"{row['Address'].strip()}, {city}, {state}"
                price = row.get("Retail Price")
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = None

                unique_id = (name, address)
                if unique_id in seen:
                    continue
                seen.add(unique_id)

                station = FuelStation(
                    name=name,
                    address=address,
                    price=price,
                    lat=None,
                    lon=None
                )
                stations_to_create.append(station)

        FuelStation.objects.bulk_create(stations_to_create, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(stations_to_create)} stations"))
