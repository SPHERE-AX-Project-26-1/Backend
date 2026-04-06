from django.shortcuts import render

from pathlib import Path
import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import requests


# 추후에 수정 가능
MAX_VIDEO_SIZE = 500 * 1024 * 1024

# FastAPI 개발 후 수정 예정
def send_to_fast_api(file_path):
    url = f"{settings.FAST_BASE_URL}/api/videos"
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'video/mp4')}
        response = requests.post(url, files=files)
    return response


class VideoUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("video_file")
        title = request.data.get("title", "").strip()

        if not uploaded_file:
            return Response(
                {"error": "video_file 파일이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext != ".mp4":
            return Response(
                {"error": "mp4 파일만 업로드할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > MAX_VIDEO_SIZE:
            return Response(
                {"error": "파일 크기는 500MB 이하여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        save_dir = Path(settings.MEDIA_ROOT) / "video"
        save_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex}{ext}"
        storage = FileSystemStorage(location=save_dir)
        saved_name = storage.save(unique_name, uploaded_file)

        saved_file_path = str(save_dir / saved_name)
        relative_file_path = f"video/{saved_name}"
        video_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{relative_file_path}")

        fastapi_result = trigger_fastapi_later(saved_file_path)

        return Response(
            {
                "message": "업로드 성공",
                "title": title,
                "original_file_name": uploaded_file.name,
                "saved_file_name": saved_name,
                "relative_file_path": relative_file_path,
                "saved_file_path": saved_file_path,
                "video_url": video_url,
                "fastapi": fastapi_result,
            },
            status=status.HTTP_201_CREATED,
        )
