from django.db import models

from django.conf import settings
from accounts.models import User

# Create your models here.
# class Video(models.Model):
#     filename = models.CharField(max_length=255)
#     file = models.FileField(upload_to='videos/')
#     thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)

#     date = models.DateField()
#     region = models.CharField(max_length=100)

#     fish_count = models.IntegerField(default=0)
#     total_count = models.IntegerField(default=0)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.filename

class Event(models.Model):
    class Type(models.TextChoices):
        UPLOAD = "UPLOAD", "업로드"
        DOWNLOAD = "DOWNLOAD", "다운로드"
        LOGIN = "LOGIN", "로그인"
        LOGOUT = "LOGOUT", "로그아웃"
        ANALYSIS = "ANALYSIS", "분석"
        DELETE = "DELETE", "삭제"


    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    detail = models.TextField()  # 로그 상세 내용
    type = models.CharField(
        max_length=20,
        choices=Type.choices
    )  # 로그 유형
    created_at = models.DateTimeField(auto_now_add=True)  # 로그 발생 시각

    # event_type = models.CharField(max_length=100)  # 이벤트 종류
    # message = models.TextField()                  # 상세 내용
    # user_id = models.IntegerField(null=True, blank=True)  # 사용자 ID
    # created_at = models.DateTimeField(auto_now_add=True)  # 발생 일시

    def __str__(self):
        return f"{self.created_at} - {self.type}"     

