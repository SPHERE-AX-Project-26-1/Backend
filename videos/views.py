from django.shortcuts import render

from pathlib import Path
import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
import requests

from .models import Region, Video
from .serializers import RegionListSerializer, VideoUploadRequestSerializer


MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi"}

# FastAPI 개발 후 수정 예정
def send_to_fast_api(file_path: str) -> dict:
    url = f"{settings.FAST_BASE_URL}/api/track"
    payload = {
        "video_path": video_path,
        "conf": 0.25,
        "imgsz": 640,
        "vid_stride": 1,
        "include_frames": False,
        "save_thumbnail": True,
        "save_annotated": False,
        "tracker": "botsort.yaml",
        "iou": 0.7,
    }
    response = requests.post(
        url,
        json=payload,
        timeout=300,
    )

    response.raise_for_status()
    return response.json()

def get_video_mime_type(ext):
    if ext == ".mp4":
        return "video/mp4"
    if ext == ".avi":
        return "video/x-msvideo"
    return "application/octet-stream"


class VideoUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        river_id = request.data.get("riverId")
        duration = request.data.get("duration")

        # 필수 데이터 검증
        if uploaded_file is None or river_id in (None, "") or duration in (None, ""):
            return Response(
                {
                    "message": "필수 입력값을 확인해주세요."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # riverId 정수 변환 및 REGION 존재 검증
        # try:
        #     river_id = int(river_id)
        # except (TypeError, ValueError):
        #     return Response(
        #         {
        #             "message": "riverId는 정수여야 합니다."
        #         },
        #         status=drf_status.HTTP_400_BAD_REQUEST,
        #     )

        # region = get_object_or_404(Region, id=river_id)

        # duration 정수 변환 및 검증
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            return Response(
                {
                    "message": "duration은 정수여야 합니다."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if duration <= 0:
            return Response(
                {
                    "message": "duration은 0보다 커야 합니다."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # 파일 확장자 검증
        original_file_name = uploaded_file.name
        ext = Path(original_file_name).suffix.lower()

        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            return Response(
                {
                    "message": "지원하지 않는 파일 형식입니다."
                },
                status=drf_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        # 파일 크기 검증
        if uploaded_file.size > MAX_VIDEO_SIZE:
            return Response(
                {
                    "message": "파일 용량이 제한을 초과했습니다."
                },
                status=drf_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        save_dir = Path(settings.MEDIA_ROOT) / "video"
        save_dir.mkdir(parents=True, exist_ok=True)

        stored_file_name = f"{uuid.uuid4().hex}{ext}"
        storage = FileSystemStorage(location=save_dir)
        saved_name = storage.save(stored_file_name, uploaded_file)

        absolute_file_path = str((save_dir / saved_name).resolve())
        relative_file_path = f"video/{saved_name}"
        title = Path(original_file_name).stem

        video = Video.objects.create(
            user=request.user,
            region=region,
            title=title,
            original_file_name=original_file_name,
            stored_file_name=saved_name,
            file_path=relative_file_path,
            thumbnail_path="",
            file_size=uploaded_file.size,
            duration=duration,
            weather="",
            fish_count=0,
            skygazer_count=0,
            status=Video.Status.PROCESSING,
        )

        # FastAPI 분석 API 호출
        try:
            fastapi_result = call_fastapi_track(absolute_file_path)

            if fastapi_result.get("status") != "success":
                raise RuntimeError("FastAPI 분석 결과 status가 success가 아닙니다.")

            fish_count = int(fastapi_result.get("fish_count") or 0)
            skygazer_count = extract_skygazer_count(fastapi_result)

            thumbnail_path = fastapi_result.get("thumbnail_path") or ""
            weather = fastapi_result.get("weather") or ""

            video.fish_count = fish_count
            video.skygazer_count = skygazer_count
            video.thumbnail_path = thumbnail_path
            video.weather = weather
            video.status = Video.Status.COMPLETED

            video.save(
                update_fields=[
                    "fish_count",
                    "skygazer_count",
                    "thumbnail_path",
                    "weather",
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "id": video.id,
                    "status": video.status,
                    "message": "영상 업로드 및 분석이 완료되었습니다."
                },
                status=drf_status.HTTP_201_CREATED,
            )

        except Exception as e:
            video.status = Video.Status.FAILED
            video.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "id": video.id,
                    "status": video.status,
                    "message": "AI 영상 분석에 실패했습니다.",
                    "detail": str(e),
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )
