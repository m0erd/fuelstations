import csv
import time
from django.core.management.base import BaseCommand
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from api.models import FuelStation


class Command(BaseCommand):
    help = "Load stations from CSV with geocoding (slow, but once only)"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **kwargs):
        csv_path = kwargs["csv_path"]
        geolocator = Nominatim(user_agent="fuel_app")

        seen = set()
        to_create = []

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                name = row["Truckstop Name"].strip()
                city = row["City"].strip()
                state = row["State"].strip()
                address = row["Address"].strip()
                price = row.get("Retail Price")
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = None

                full_address = f"{address}, {city}, {state}, USA"
                if (name, full_address) in seen:
                    continue
                seen.add((name, full_address))

                try:
                    location = geolocator.geocode(full_address, timeout=10)
                except GeocoderTimedOut:
                    time.sleep(1)
                    continue

                if location:
                    station = FuelStation(
                        name=name,
                        address=address,
                        city=city,
                        state=state,
                        price=price,
                        lat=location.latitude,
                        lon=location.longitude
                    )
                    to_create.append(station)
                time.sleep(1)

                if i % 50 == 0:
                    self.stdout.write(f"{i} rows processed...")

        FuelStation.objects.bulk_create(to_create, batch_size=200)
        self.stdout.write(self.style.SUCCESS(f"Inserted {len(to_create)} stations."))
