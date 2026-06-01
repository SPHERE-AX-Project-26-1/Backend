from django.db import models


class Region(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "LOW"
        MEDIUM = "MEDIUM", "MEDIUM"
        HIGH = "HIGH", "HIGH"

    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)  # API에서는 region으로 응답
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW
    )

    caution_threshold = models.IntegerField(default=5)
    danger_threshold = models.IntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "REGION"

    def __str__(self):
        return self.names