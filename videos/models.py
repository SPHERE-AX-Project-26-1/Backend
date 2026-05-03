from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

class Region(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "LOW"
        MEDIUM = "MEDIUM", "MEDIUM"
        HIGH = "HIGH", "HIGH"

    id = models.BigAutoField(primary_key=True)

    region_name = models.CharField(max_length=100)

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
        return self.region_name


class Video(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "PROCESSING"
        COMPLETED = "COMPLETED", "COMPLETED"
        FAILED = "FAILED", "FAILED"

    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="videos"
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        db_column="region_id",
        related_name="videos"
    )

    title = models.CharField(max_length=255)

    original_file_name = models.CharField(max_length=255)
    stored_file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    thumbnail_path = models.CharField(max_length=500, blank=True)

    file_size = models.BigIntegerField(
        validators=[MinValueValidator(0)]
    )

    weather = models.CharField(max_length=50, blank=True)

    duration = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    fish_count = models.BigIntegerField(default=0)
    skygazer_count = models.BigIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "VIDEO"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.id} - {self.title}"
