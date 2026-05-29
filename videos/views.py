from time import timezone

from django.shortcuts import render

from pathlib import Path
import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
import requests

from .models import Video, DetectedTime
from regions.models import Region


MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi"}
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def call_fastapi(file_path: str) -> dict:
    url = f"{settings.FAST_BASE_URL.rstrip('/')}/api/analyze"

    payload = {
        "video_path": file_path,
        "conf": 0.25,
        "cls_conf": 0.0,
        "imgsz": 640,
        "cls_imgsz": 224,
        "vid_stride": 1,
        "include_frames": False,
        "save_thumbnail": True,
        "tracker": "botsort.yaml",
        "iou": 0.7,
        "crop_margin": 0.15,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=getattr(settings, "FASTAPI_ANALYZE_TIMEOUT", 900),
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"FastAPI 서버 호출 실패 : {e}")

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text

        raise RuntimeError(
            f"FastAPI 분석 요청 실패 : status={response.status_code}, detail={detail}"
        )

    try:
        return response.json()
    except ValueError:
        raise RuntimeError("FastAPI 응답이 JSON 형식 오류")

def get_video_mime_type(ext):
    if ext == ".mp4":
        return "video/mp4"
    if ext == ".avi":
        return "video/x-msvideo"
    return "application/octet-stream"

def convert_to_int_seconds(value, default=0):
    if value is None:
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default
    

# 개체 탐지 시간 DB에 저장하는 함수
def save_detected_times(video: Video, fastapi_result: dict):
    tracks = fastapi_result.get("tracks") or []

    detected_time_objects = []

    for track in tracks:
        fish_type = track.get("species") or "others"

        start_time = convert_to_int_seconds(track.get("first_time_sec"), default=0)
        end_time = convert_to_int_seconds(track.get("last_time_sec"), default=start_time)

        if end_time < start_time:
            end_time = start_time


        detected_time_objects.append(
            DetectedTime(
                video=video,
                fish_type=fish_type,
                start_time=start_time,
                end_time=end_time,
            )
        )

    if detected_time_objects:
        DetectedTime.objects.bulk_create(detected_time_objects)

def parse_weather_code_to_enum(weather_code: int) -> str:

    if weather_code == 0:
        return "CLEAR"

    if weather_code in {1, 2, 3}:
        return "CLOUDY"

    if weather_code in {45, 48}:
        return "FOG"

    if weather_code in {71, 73, 75, 77, 85, 86}:
        return "SNOW"

    if weather_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 
        67, 80, 81, 82, 95, 96, 99}:
        return "RAIN"

    return "CLOUDY"

def fetch_weather_by_date_and_location(target_date, latitude, longitude) -> str:

    date_str = target_date.isoformat()

    params = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "start_date": date_str,
        "end_date": date_str,
        "daily": "weather_code",
        "timezone": "Asia/Seoul",
    }

    try:
        response = requests.get(
            OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=5,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        raise ValidationError({
            "weather": f"날씨 API 호출에 실패했습니다: {str(e)}"
        })

    data = response.json()

    try:
        weather_codes = data["daily"]["weather_code"]
        weather_code = weather_codes[0]

    except (KeyError, IndexError, TypeError):
        raise ValidationError({
            "weather": "날씨 API 응답에서 weather_code를 찾을 수 없습니다."
        })

    if weather_code is None:
        raise ValidationError({
            "weather": "해당 날짜와 위치의 날씨 데이터가 비어 있습니다."
        })

    return parse_weather_code_to_enum(int(weather_code))



class VideoUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        river_id = request.data.get("riverId")
        duration = request.data.get("duration")
        date = request.data.get("date")

        # 필수 데이터 검증
        if uploaded_file is None or river_id in (None, "") or duration in (None, "") or date in (None, ""):
            return Response(
                {
                    "message": "필수 입력값을 확인해주세요."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # riverId 정수 변환 및 REGION 존재 검증
        try:
            river_id = int(river_id)
        except (TypeError, ValueError):
            return Response(
                {
                    "message": "riverId는 정수여야 합니다."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        region = get_object_or_404(Region, id=river_id)

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

        # date 파싱 및 검증
        try:
            date = parse_date(date)
        except (TypeError, ValueError):
            return Response(
                {
                    "message": "date는 YYYY-MM-DD 형식이어야 합니다. 예: 2026-03-15"
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        if date is None:
            return Response(
                {
                    "message": "date는 YYYY-MM-DD 형식이어야 합니다. 예: 2026-03-15"
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

        
        # 날씨 정보 가져오기
        try:
            weather = fetch_weather_by_date_and_location(
                target_date=date,
                latitude=region.latitude,
                longitude=region.longitude, 
            )
        except ValidationError as e:
            return Response(
                {
                    "message": "날씨 정보를 가져오지 못했습니다.",
                    "detail": e.detail,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
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
            weather=weather,
            duration=duration,
            date=date,
            fish_count=0,
            skygazer_count=0,
            status=Video.Status.PROCESSING,
        )

        # FastAPI 분석 API 호출
        try:
            fastapi_result = call_fastapi(absolute_file_path)

            if fastapi_result.get("status") != "success":
                raise RuntimeError("FastAPI 분석 결과가 success가 아닙니다.")

            fish_count = int(fastapi_result.get("fish_count") or 0)
            skygazer_count = int(fastapi_result.get("skygazer_count") or 0)

            thumbnail_path = fastapi_result.get("thumbnail_path") or ""

            video.fish_count = fish_count
            video.skygazer_count = skygazer_count
            video.thumbnail_path = thumbnail_path
            video.status = Video.Status.COMPLETED

            video.save(
                update_fields=[
                    "fish_count",
                    "skygazer_count",
                    "thumbnail_path",
                    "status",
                    "updated_at",
                ]
            )
            save_detected_times(video, fastapi_result)

            return Response(
                {
                    "id": video.id,
                    "status": video.status,
                    "skygazerCount": video.skygazer_count,
                    "message": "영상 업로드 및 분석이 완료되었습니다.",
                    # "result": {
                    #     "fishCount": video.fish_count,
                    #     "skygazerCount": video.skygazer_count,
                    #     "thumbnailPath": video.thumbnail_path,
                    # },
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
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )
