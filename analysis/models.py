from django.db import models

# Create your models here.
class Video(models.Model):
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)

    date = models.DateField()
    region = models.CharField(max_length=100)

    fish_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

class SystemLog(models.Model):
    event_type = models.CharField(max_length=100)  # 이벤트 종류
    message = models.TextField()                  # 상세 내용
    user_id = models.IntegerField(null=True, blank=True)  # 사용자 ID
    created_at = models.DateTimeField(auto_now_add=True)  # 발생 일시

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"        

class Basin(models.Model):
    name = models.CharField(max_length=100)  # 유역명
    region = models.CharField(max_length=100)  # 지역
    latitude = models.FloatField()
    longitude = models.FloatField()
    severity = models.CharField(max_length=10, default="LOW")  # 위험도
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name