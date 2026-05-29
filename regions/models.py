from django.db import models

# class Basin(models.Model):
#     name = models.CharField(max_length=100)  # 유역명
#     address = models.CharField(max_length=100)  # 지역
#     latitude = models.FloatField()
#     longitude = models.FloatField()
#     risk_level = models.CharField(max_length=10, default="LOW")  # 위험도
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

class Region(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "LOW"
        MEDIUM = "MEDIUM", "MEDIUM"
        HIGH = "HIGH", "HIGH"

    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7
    )

    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "REGION"

    def __str__(self):
        return self.name
