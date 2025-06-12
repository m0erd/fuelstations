from django.urls import path
from .views import RouteFuelStopsAPIView

urlpatterns = [
    path("route/", RouteFuelStopsAPIView.as_view(), name="route-fuel_stops"),
]
