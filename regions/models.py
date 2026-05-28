from django.db import models

class Basin(models.Model):
    name = models.CharField(max_length=100)  # 유역명
    address = models.CharField(max_length=100)  # 지역
    latitude = models.FloatField()
    longitude = models.FloatField()
    risk_level = models.CharField(max_length=10, default="LOW")  # 위험도
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name