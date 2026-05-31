from django.db.models import (
    Sum,
    Value,
    BigIntegerField,
    Q,
    OuterRef,
    Subquery,
    DateTimeField,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

# video 모델 merge 필요
from videos.models import Video
from regions.models import Region


RISK_DB_TO_LABEL = {
    Region.RiskLevel.LOW: "보통",
    Region.RiskLevel.MEDIUM: "주의",
    Region.RiskLevel.HIGH: "위험",
}

RISK_LABEL_TO_DB = {
    "보통": Region.RiskLevel.LOW,
    "주의": Region.RiskLevel.MEDIUM,
    "위험": Region.RiskLevel.HIGH,
    "LOW": Region.RiskLevel.LOW,
    "MEDIUM": Region.RiskLevel.MEDIUM,
    "HIGH": Region.RiskLevel.HIGH,
}

STATUS_BY_RISK = {
    Region.RiskLevel.LOW: "정상",
    Region.RiskLevel.MEDIUM: "모니터링 필요",
    Region.RiskLevel.HIGH: "즉시 점검 필요",
}

WEATHER_DB_TO_LABEL = {
    Video.Weather.CLEAR: "맑음",
    Video.Weather.CLOUDY: "흐림",
    Video.Weather.RAIN: "비",
    Video.Weather.SNOW: "눈",
    Video.Weather.FOG: "안개",
}


def get_completed_video_queryset():
    return Video.objects.filter(status=Video.Status.COMPLETED)

def get_total_skygazer_count(qs):
    return qs.aggregate(
        total=Coalesce(
            Sum("skygazer_count"),
            Value(0, output_field=BigIntegerField()),
            output_field=BigIntegerField(),
        )
    )["total"]

def format_date(value):
    if value is None:
        return ""

    if timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d")


def format_datetime_minute(value):
    if value is None:
        return ""

    if timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d %H:%M")


def format_duration(seconds):
    if seconds is None:
        return ""

    seconds = int(seconds)
    minutes, remain_seconds = divmod(seconds, 60)

    if minutes > 0:
        return f"{minutes}분 {remain_seconds}초"

    return f"{remain_seconds}초"

def validate_risk_param(risk):
    if risk in (None, ""):
        return None

    risk = str(risk).strip()

    if risk not in RISK_LABEL_TO_DB:
        raise ValueError("위험도 값이 올바르지 않습니다.")

    return RISK_LABEL_TO_DB[risk]

def get_dashboard_summary():
    completed_videos = get_completed_video_queryset()

    total_river_count = Region.objects.count()

    detected_river_count = (
        Region.objects
        .filter(
            videos__status=Video.Status.COMPLETED,
            videos__skygazer_count__gt=0,
        )
        .distinct()
        .count()
    )

    danger_river_count = Region.objects.filter(
        risk_level=Region.RiskLevel.HIGH
    ).count()

    total_skygazer_count = get_total_skygazer_count(completed_videos)

    return {
        "totalRiverCount": total_river_count,
        "detectedRiverCount": detected_river_count,
        "dangerRiverCount": danger_river_count,
        "totalSkygazerCount": int(total_skygazer_count or 0),
    }


def get_regions_with_dashboard_stats():
    latest_completed_video = (
        Video.objects
        .filter(
            region_id=OuterRef("pk"),
            status=Video.Status.COMPLETED,
        )
        .order_by("-updated_at", "-created_at", "-id")
    )

    return (
        Region.objects
        .annotate(
            total_skygazer_count=Coalesce(
                Sum(
                    "videos__skygazer_count",
                    filter=Q(videos__status=Video.Status.COMPLETED),
                ),
                Value(0, output_field=BigIntegerField()),
                output_field=BigIntegerField(),
            ),
            latest_video_id=Subquery(
                latest_completed_video.values("id")[:1],
                output_field=BigIntegerField(),
            ),
            latest_video_analyzed_at=Subquery(
                latest_completed_video.values("updated_at")[:1],
                output_field=DateTimeField(),
            ),
            latest_skygazer_count=Coalesce(
                Subquery(
                    latest_completed_video.values("skygazer_count")[:1],
                    output_field=BigIntegerField(),
                ),
                Value(0, output_field=BigIntegerField()),
                output_field=BigIntegerField(),
            ),
        )
    )


def serialize_river_marker(region):
    risk_label = RISK_DB_TO_LABEL.get(region.risk_level, region.risk_level)
    status_label = STATUS_BY_RISK.get(region.risk_level, "정상")

    return {
        "id": region.id,
        "name": region.name,
        "address": region.address,
        "latitude": float(region.latitude),
        "longitude": float(region.longitude),
        "lastAnalyzedAt": format_date(region.latest_video_analyzed_at),
        "totalSkygazerCount": int(region.total_skygazer_count or 0),
        "latestSkygazerCount": int(region.latest_skygazer_count or 0),
        "risk": risk_label,
        "status": status_label,
        "latestVideoId": region.latest_video_id,
    }


def get_dashboard_rivers(risk=None):
    risk_db_value = validate_risk_param(risk)

    qs = get_regions_with_dashboard_stats()

    if risk_db_value is not None:
        qs = qs.filter(risk_level=risk_db_value)

    qs = qs.order_by("id")

    return {
        "items": [
            serialize_river_marker(region)
            for region in qs
        ]
    }

def parse_limit(limit):
    if limit in (None, ""):
        return 3

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError("limit은 정수여야 합니다.")

    if limit <= 0:
        raise ValueError("limit은 1 이상이어야 합니다.")

    return min(limit, 20)


def serialize_top_river(region):
    risk_label = RISK_DB_TO_LABEL.get(region.risk_level, region.risk_level)

    return {
        "id": region.id,
        "name": region.name,
        "totalSkygazerCount": int(region.total_skygazer_count or 0),
        "risk": risk_label,
    }


def get_top_rivers(limit=None):
    limit = parse_limit(limit)

    qs = (
        get_regions_with_dashboard_stats()
        .filter(total_skygazer_count__gt=0)
        .order_by("-total_skygazer_count", "id")[:limit]
    )

    return {
        "items": [
            serialize_top_river(region)
            for region in qs
        ]
    }
