from django.db import models

class FuelStation(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    price = models.FloatField(null=True, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"
