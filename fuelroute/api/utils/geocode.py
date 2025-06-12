import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("EMAIL")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "geocode_cache.json")

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        geocode_cache = json.load(f)
else:
    geocode_cache = {}

def geocode_address(address):
    if address in geocode_cache:
        return geocode_cache[address]

    geocode_url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"
    headers = {
        "User-Agent": EMAIL or "fuelroute-app"
    }

    try:
        response = requests.get(geocode_url, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()

        if not results:
            return None

        lon = float(results[0]["lon"])
        lat = float(results[0]["lat"])
        coordinates = [lon, lat]

        geocode_cache[address] = coordinates

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(geocode_cache, f, indent=2)

        return coordinates

    except requests.RequestException as e:
        print(f"Geocoding failed for {address}: {e}")
        return None
