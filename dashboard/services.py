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
from videos.models import Video, Region


RISK_DB_TO_LABEL = {
    Region.RiskLevel.LOW: "보통",
    Region.RiskLevel.MEDIUM: "주의",
    Region.RiskLevel.HIGH: "위험",
}

RISK_LABEL_TO_DB = {
    "보통": Region.RiskLevel.LOW,
    "주의": Region.RiskLevel.MEDIUM,
    "위험": Region.RiskLevel.HIGH,
}

STATUS_BY_RISK = {
    Region.RiskLevel.LOW: "정상",
    Region.RiskLevel.MEDIUM: "모니터링 필요",
    Region.RiskLevel.HIGH: "즉시 점검 필요",
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

    total_detected_count = get_total_skygazer_count(completed_videos)

    return {
        "totalRiverCount": total_river_count,
        "detectedRiverCount": detected_river_count,
        "dangerRiverCount": danger_river_count,
        "totalDetectedCount": int(total_detected_count),
    }


def validate_risk_param(risk):
    if risk in (None, ""):
        return None

    if risk not in RISK_LABEL_TO_DB:
        raise ValueError("위험도 값이 올바르지 않습니다.")

    return RISK_LABEL_TO_DB[risk]


def format_last_date(dt):
    if dt is None:
        return ""

    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)

    return dt.strftime("%Y-%m-%d")


def get_regions_with_dashboard_stats():
    latest_completed_video = (
        Video.objects
        .filter(
            region_id=OuterRef("pk"),
            status=Video.Status.COMPLETED,
        )
        .order_by("-created_at", "-id")
    )

    return (
        Region.objects
        .annotate(
            detect_count=Coalesce(
                Sum(
                    "videos__skygazer_count",
                    filter=Q(videos__status=Video.Status.COMPLETED),
                ),
                Value(0, output_field=BigIntegerField()),
                output_field=BigIntegerField(),
            ),
            latest_video_id=Subquery(
                latest_completed_video.values("id")[:1]
            ),
            latest_video_created_at=Subquery(
                latest_completed_video.values("created_at")[:1],
                output_field=DateTimeField(),
            ),
        )
    )


def serialize_river_marker(region):
    risk_label = RISK_DB_TO_LABEL.get(region.risk_level, region.risk_level)
    status_label = STATUS_BY_RISK.get(region.risk_level, "정상")

    latitude = float(region.latitude)
    longitude = float(region.longitude)

    return {
        "id": region.id,
        "region": region.region_name,
        "latitude": latitude,
        "longitude": longitude,
        "lastDate": format_last_date(region.latest_video_created_at),
        "detectCount": int(region.detect_count or 0),
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
        "name": region.region_name,
        "detectCount": int(region.detect_count or 0),
        "risk": risk_label,
    }


def get_top_rivers(limit=None):
    limit = parse_limit(limit)

    qs = (
        get_regions_with_dashboard_stats()
        .filter(detect_count__gt=0)
        .order_by("-detect_count", "region_name")[:limit]
    )

    return {
        "items": [
            serialize_top_river(region)
            for region in qs
        ]
    }
