import json
import csv
import os
import requests
from time import sleep
from math import radians, cos, sin
from typing import List, Dict, Tuple, Optional
from geopy.distance import geodesic
from dotenv import load_dotenv
from geopy.distance import distance as geopy_distance
from scipy.spatial import KDTree
from .geocode import geocode_address

load_dotenv()

ORS_API_KEY = os.getenv("ORS_API_KEY")
EMAIL = os.getenv("EMAIL")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
GEOCODE_CACHE_FILE = os.path.join(CACHE_DIR, "geocode_cache.json")
ROUTE_CACHE_FILE = os.path.join(CACHE_DIR, "route_cache.json")
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    with open(ROUTE_CACHE_FILE, "r", encoding="utf-8") as f:
        route_cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    route_cache = {}


def save_json_atomic(data: dict, filepath: str):
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, filepath)


def cache_route(start: str, end: str, data: dict):
    key = f"{start}__{end}"
    route_cache[key] = data
    save_json_atomic(route_cache, ROUTE_CACHE_FILE)


def get_route(start: str, end: str) -> Optional[dict]:
    key = f"{start}__{end}"
    if key in route_cache:
        return route_cache[key]

    start_coordinates = geocode_address(start)
    end_coordinates = geocode_address(end)
    if not start_coordinates or not end_coordinates:
        print("Failed geocoding")
        return None

    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "coordinates": [start_coordinates, end_coordinates]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        cache_route(start, end, data)
        return data
    except requests.RequestException as e:
        print(f"Route request failed: {e}")
        return None


def load_fuel_stations(csv_path: str) -> List[Dict]:
    seen = set()
    stations = []

    try:
        with open(GEOCODE_CACHE_FILE, "r", encoding="utf-8") as f:
            geocode_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        geocode_cache = {}

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                name = row.get("Truckstop Name")
                city = row.get("City")
                state = row.get("State")
                raw_address = row.get("Address")
                price_raw = row.get("Retail Price")

                if not all([name, city, state, raw_address, price_raw]):
                    continue

                address = f"{raw_address}, {city}, {state}"
                unique_id = (name, address)
                if unique_id in seen:
                    continue
                seen.add(unique_id)

                price = float(price_raw)
                lat_lon = geocode_cache.get(address)

                if not lat_lon:
                    sleep(1)
                    resp = requests.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": address, "format": "json", "limit": 1},
                        headers={"User-Agent": "fuelroute-app"}
                    )
                    geo = resp.json()
                    if geo:
                        lat_lon = (float(geo[0]["lat"]), float(geo[0]["lon"]))
                        geocode_cache[address] = lat_lon
                    else:
                        print(f"No geocode result: {address}")
                        continue

                station = {
                    "name": name,
                    "address": address,
                    "price": price,
                    "lat": lat_lon[0],
                    "lon": lat_lon[1]
                }
                stations.append(station)
            except Exception as e:
                print(f"Error parsing station: {e}")

    save_json_atomic(geocode_cache, GEOCODE_CACHE_FILE)
    return stations


EARTH_RADIUS = 3959  # in miles


def latlon_to_cartesian(lat: float, lon: float) -> List[float]:
    lat_rad = radians(lat)
    lon_rad = radians(lon)
    x = EARTH_RADIUS * cos(lat_rad) * cos(lon_rad)
    y = EARTH_RADIUS * cos(lat_rad) * sin(lon_rad)
    z = EARTH_RADIUS * sin(lat_rad)
    return [x, y, z]


def build_kdtree(stations: List[Dict]) -> KDTree:
    points = [latlon_to_cartesian(s['lat'], s['lon']) for s in stations]
    return KDTree(points)


def find_best_stations(route_coords: List[List[float]], stations: List[Dict], max_detour_miles=5) -> List[Dict]:
    if not route_coords or not stations:
        return []

    tree = build_kdtree(stations)
    radians_detour = radians(max_detour_miles / EARTH_RADIUS)
    chord_length = 2 * EARTH_RADIUS * sin(radians_detour / 2)

    best_station_indices = set()
    for lon, lat in route_coords:
        point_cartesian = latlon_to_cartesian(lat, lon)
        nearby_idxs = tree.query_ball_point(point_cartesian, r=chord_length)
        for idx in nearby_idxs:
            station = stations[idx]
            actual_distance = geopy_distance((lat, lon), (station["lat"], station["lon"])).miles
            if actual_distance <= max_detour_miles:
                best_station_indices.add(idx)

    print(f"Found {len(best_station_indices)} matching stations")
    return sorted([stations[i] for i in best_station_indices], key=lambda s: s["price"])


def is_near_route(station_coords: Tuple[float, float], route_coords: List[List[float]], max_detour_miles=5) -> bool:
    return any(
        geodesic(station_coords, (coord[1], coord[0])).miles <= max_detour_miles
        for coord in route_coords
    )


def plan_fuel_stops(route_coords, fuel_stations, max_range, detour_radius=10):
    route_coords_latlon = [(coord[1], coord[0]) for coord in route_coords]
    route_coords_latlon = route_coords_latlon[::10]

    lats = [pt[0] for pt in route_coords_latlon]
    lons = [pt[1] for pt in route_coords_latlon]
    lat_min, lat_max = min(lats) - 0.5, max(lats) + 0.5
    lon_min, lon_max = min(lons) - 0.5, max(lons) + 0.5
    fuel_stations = [
        s for s in fuel_stations
        if lat_min <= s['lat'] <= lat_max and lon_min <= s['lon'] <= lon_max
    ]

    fuel_stops = []
    current_pos = route_coords_latlon[0]
    destination = route_coords_latlon[-1]

    def stations_near_point(route_point):
        nearby = []
        for station in fuel_stations:
            station_pos = (station['lat'], station['lon'])
            if geodesic(route_point, station_pos).miles <= detour_radius:
                nearby.append(station)
        return nearby

    last_stop_idx = 0

    while geodesic(current_pos, destination).miles > max_range:
        candidate_route_points = []
        for i in range(last_stop_idx + 1, len(route_coords_latlon)):
            if geodesic(current_pos, route_coords_latlon[i]).miles <= max_range:
                candidate_route_points.append((i, route_coords_latlon[i]))
            else:
                break

        candidate_stations = []
        for idx, rp in candidate_route_points:
            nearby_stations = stations_near_point(rp)
            for s in nearby_stations:
                station_pos = (s['lat'], s['lon'])
                if geodesic(current_pos, station_pos).miles <= max_range:
                    candidate_stations.append((s, idx))

        if not candidate_stations:
            print("No reachable fuel stations within constraints, route planning stops.")
            break

        def score(station_info):
            s, idx = station_info
            station_pos = (s['lat'], s['lon'])
            route_point = route_coords_latlon[idx]
            detour_dist = geodesic(station_pos, route_point).miles
            return s['price'] + detour_dist * 0.1

        best_station, best_idx = min(candidate_stations, key=score)

        fuel_stops.append(best_station)
        current_pos = (best_station['lat'], best_station['lon'])
        last_stop_idx = best_idx

    return fuel_stops
