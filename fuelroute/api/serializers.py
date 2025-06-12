from rest_framework import serializers
from .models import FuelStation

class FuelStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelStation
        fields = ['id', 'name', 'address', 'price', 'lat', 'lon']
