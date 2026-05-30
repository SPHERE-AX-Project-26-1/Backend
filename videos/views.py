from pathlib import Path
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
import requests

from .models import Video, DetectedTime
from regions.models import Region
from analysis.models import Event


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

def format_date(value):
    if value is None:
        return ""

    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d")

def format_datetime_minute(value):
    if value is None:
        return ""

    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d %H:%M")

def format_duration(seconds):
    if seconds is None:
        return ""

    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""

    minutes, remain_seconds = divmod(seconds, 60)
    if minutes > 0:
        return f"{minutes}분 {remain_seconds}초"

    return f"{remain_seconds}초"

def get_uploader_name(user):
    if user is None:
        return ""

    if hasattr(user, "name") and user.name:
        return user.name

    if hasattr(user, "get_full_name"):
        full_name = user.get_full_name()
        if full_name:
            return full_name

    if hasattr(user, "username") and user.username:
        return user.username

    if hasattr(user, "email") and user.email:
        return user.email

    return str(user)

def positive_int(value, default, max_value=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    if number < 1:
        number = default

    if max_value is not None:
        number = min(number, max_value)

    return number
    

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

        Event.objects.create(
            user=request.user,
            type=Event.Type.UPLOAD,
            detail=f"영상 업로드됨 (id: {video.id}, title: {video.title})"
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

            Event.objects.create(
                user=request.user,
                type=Event.Type.ANALYSIS,
                detail=f"영상 분석 완료 (id: {video.id}, title: {video.title}, fish_count: {fish_count}, skygazer_count: {skygazer_count})"
            )

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
            Event.objects.create(
                user=request.user,
                type=Event.Type.ANALYSIS,
                detail=f"영상 분석 실패 (id: {video.id}, title: {video.title}, error: {str(e)})"
            )  

            return Response(
                {
                    "id": video.id,
                    "status": video.status,
                    "message": "AI 영상 분석에 실패했습니다.",
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )


def serialize_video_for_list(video: Video):
    region = video.region

    return {
        "id": video.id,
        "filename": video.title,
        "date": format_date(video.date),
        "uploadDate": format_date(video.created_at),
        "uploadTime": format_datetime_minute(video.created_at),
        "name": region.name,
        "latitude": float(region.latitude) if region.latitude is not None else None,
        "longitude": float(region.longitude) if region.longitude is not None else None,
        "skygazerCount": int(video.skygazer_count or 0),
        "totalCount": int(video.fish_count or 0),
        "weather": video.weather,
        "duration": format_duration(video.duration),
        "uploader": get_uploader_name(video.user),
    }

def get_safe_media_file_path(relative_or_absolute_path):
    if not relative_or_absolute_path:
        return None

    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = Path(relative_or_absolute_path)

    if not file_path.is_absolute():
        file_path = media_root / file_path

    file_path = file_path.resolve()

    # MEDIA_ROOT 바깥 파일 삭제 방지
    if file_path != media_root and media_root not in file_path.parents:
        return None

    return file_path

def delete_local_file_safely(relative_or_absolute_path):
    file_path = get_safe_media_file_path(relative_or_absolute_path)

    if file_path is None:
        return

    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
    except OSError:
        pass

class VideoListDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        videos = Video.objects.select_related("region", "user").all()

        search = request.query_params.get("search", "").strip()
        region = request.query_params.get("region", "").strip()
        sort_by = request.query_params.get("sortBy", "date_desc").strip()

        if search:
            videos = videos.filter(region__name__icontains=search)

        if region:
            videos = videos.filter(region__name=region)

        if sort_by == "date_asc":
            videos = videos.order_by("date", "id")

        elif sort_by == "region":
            videos = videos.order_by("region__name", "-date", "-id")

        else:
            videos = videos.order_by("-date", "-id")

        total = videos.count()

        page = positive_int(
            request.query_params.get("page"),
            default=1,
        )

        page_size = positive_int(
            request.query_params.get("pageSize"),
            default=8,
            max_value=100,
        )

        start = (page - 1) * page_size
        end = start + page_size

        items = [
            serialize_video_for_list(video)
            for video in videos[start:end]
        ]

        return Response(
            {
                "total": total,
                "items": items,
            },
            status=drf_status.HTTP_200_OK,
        )

    def delete(self, request):
        ids = request.data.get("ids")

        if not isinstance(ids, list) or len(ids) == 0:
            return Response(
                {
                    "message": "삭제할 영상 ID 배열이 필요합니다."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        try:
            ids = [int(video_id) for video_id in ids]
        except (TypeError, ValueError):
            return Response(
                {
                    "message": "ids는 정수 배열이어야 합니다."
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # 중복 제거
        ids = list(dict.fromkeys(ids))

        videos = list(Video.objects.filter(id__in=ids).select_related("region", "user"))
        found_ids = {video.id for video in videos}
        missing_ids = [video_id for video_id in ids if video_id not in found_ids]

        if missing_ids:
            return Response(
                {
                    "message": "존재하지 않는 영상입니다."
                },
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        file_paths_to_delete = []

        for video in videos:
            if video.file_path:
                file_paths_to_delete.append(video.file_path)

            if video.thumbnail_path:
                file_paths_to_delete.append(video.thumbnail_path)

        with transaction.atomic():
            for video in videos:
                Event.objects.create(
                    user=request.user,
                    type=Event.Type.DELETE,
                    detail=f"영상 삭제됨 (id: {video.id}, title: {video.title})"
                )
                video.delete()

        for file_path in file_paths_to_delete:
            delete_local_file_safely(file_path)

        return Response(status=drf_status.HTTP_200_OK)


class VideoRegionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        names = (
            Region.objects
            .exclude(name__isnull=True)
            .exclude(name="")
            .values_list("name", flat=True)
            .distinct()
            .order_by("name")
        )

        return Response(
            {
                "name": list(names)
            },
            status=drf_status.HTTP_200_OK,
        )
