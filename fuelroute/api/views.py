from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import FuelStation
from .utils.route import get_route, plan_fuel_stops

CACHE_TIMEOUT = 60 * 60


class RouteFuelStopsAPIView(APIView):
    def post(self, request):
        start = request.data.get("start")
        end = request.data.get("end")

        try:
            mpg = float(request.data.get("mpg", 10))
            max_range = float(request.data.get("max_range", 500))
        except (TypeError, ValueError):
            return Response({"error": "Invalid mpg or max_range value"}, status=400)

        if not start or not end:
            return Response({"error": "Missing 'start' or 'end' parameter"}, status=400)

        cache_key = f"route:{start.lower()}:{end.lower()}:{mpg}:{max_range}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        route_data = get_route(start, end)
        if not route_data:
            return Response({"error": "Failed to retrieve route"}, status=400)

        try:
            coords = route_data["features"][0]["geometry"]["coordinates"]
            segment = route_data["features"][0]["properties"]["segments"][0]
            total_distance_miles = segment["distance"] / 1609.34
        except (KeyError, IndexError) as e:
            return Response({"error": f"Malformed route data: {e}"}, status=500)

        valid_route_coords = [
            coord for coord in coords if -180 <= coord[0] <= 180 and -90 <= coord[1] <= 90
        ]
        if not valid_route_coords:
            return Response({"error": "Invalid route coordinates received"}, status=500)

        stations = list(FuelStation.objects.values("name", "address", "price", "lat", "lon"))
        valid_stations = [
            s for s in stations if -90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180
        ]
        if not valid_stations:
            return Response({"error": "No valid fuel stations available"}, status=500)

        try:
            fuel_stops = plan_fuel_stops(
                route_coords=valid_route_coords,
                fuel_stations=valid_stations,
                max_range=max_range,
            )
        except Exception as e:
            return Response({"error": f"Error calculating fuel stops: {e}"}, status=500)

        total_gallons_needed = total_distance_miles / mpg

        if fuel_stops:
            avg_price = sum(s["price"] for s in fuel_stops) / len(fuel_stops)
        else:
            avg_price = sum(s["price"] for s in valid_stations) / len(valid_stations)

        total_cost = avg_price * total_gallons_needed

        response_data = {
            "start": start,
            "end": end,
            "mpg": mpg,
            "max_range": max_range,
            "total_distance_miles": round(total_distance_miles, 2),
            "total_gallons_needed": round(total_gallons_needed, 2),
            "estimated_fuel_cost": round(total_cost, 2),
            "fuel_stops": fuel_stops,
        }
        cache.set(cache_key, response_data, timeout=24 * 3600)
        return Response(response_data)
