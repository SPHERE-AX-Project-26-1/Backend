from datetime import timedelta

from django.db.models import Sum, Count, Max, Q, Value, BigIntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

# video 모델 merge 필요
from videos.models import Video, Region


RISK_LABEL_MAP = {
    "LOW": "보통",
    "MEDIUM": "주의",
    "HIGH": "위험",
}

RISK_DESCRIPTION_MAP = {
    "LOW": "특이사항 없음",
    "MEDIUM": "관찰 필요",
    "HIGH": "즉시 점검 필요",
}


def get_risk_label(risk_level):
    return RISK_LABEL_MAP.get(risk_level, risk_level)


def get_management_status(risk_level):
    return RISK_DESCRIPTION_MAP.get(risk_level, "상태 확인 필요")


def to_float(value):
    if value is None:
        return None
    return float(value)


def format_date(value):
    if not value:
        return None
    return timezone.localtime(value).strftime("%Y-%m-%d")


def format_short_date(value):
    if not value:
        return None
    return timezone.localtime(value).strftime("%y.%m.%d")


def format_time(value):
    if not value:
        return None
    return timezone.localtime(value).strftime("%H:%M")


def completed_videos():
    return Video.objects.select_related("region").filter(status="COMPLETED")


def get_dashboard_markers(risk=None):
    regions = Region.objects.all()

    if risk and risk != "ALL":
        regions = regions.filter(risk_level=risk)

    regions = regions.annotate(
        total_detected=Coalesce(
            Sum(
                "video__skygazer_count",
                filter=Q(video__status="COMPLETED"),
            ),
            Value(0),
            output_field=BigIntegerField(),
        ),
        total_fish=Coalesce(
            Sum(
                "video__fish_count",
                filter=Q(video__status="COMPLETED"),
            ),
            Value(0),
            output_field=BigIntegerField(),
        ),
        analysis_video_count=Count(
            "video",
            filter=Q(video__status="COMPLETED"),
        ),
        latest_analyzed_at=Max(
            "video__created_at",
            filter=Q(video__status="COMPLETED"),
        ),
    ).order_by("id")

    region_ids = [region.id for region in regions]

    latest_video_map = {}
    latest_videos = (
        completed_videos()
        .filter(region_id__in=region_ids)
        .order_by("region_id", "-created_at")
    )

    for video in latest_videos:
        if video.region_id not in latest_video_map:
            latest_video_map[video.region_id] = video

    markers = []

    for region in regions:
        latest_video = latest_video_map.get(region.id)

        markers.append(
            {
                "id": region.id,
                "regionName": region.region_name,
                "latitude": to_float(region.latitude),
                "longitude": to_float(region.longitude),
                "riskLevel": region.risk_level,
                "riskLabel": get_risk_label(region.risk_level),
                "managementStatus": get_management_status(region.risk_level),
                "totalDetected": region.total_detected,
                "totalFish": region.total_fish,
                "analysisVideoCount": region.analysis_video_count,
                "latestAnalyzedAt": format_date(region.latest_analyzed_at),
                "latestVideoId": latest_video.id if latest_video else None,
            }
        )

    return markers


def get_region_detail(region_id):
    region = get_object_or_404(Region, id=region_id)

    videos = completed_videos().filter(region_id=region.id)

    aggregate = videos.aggregate(
        total_detected=Coalesce(
            Sum("skygazer_count"),
            Value(0),
            output_field=BigIntegerField(),
        ),
        total_fish=Coalesce(
            Sum("fish_count"),
            Value(0),
            output_field=BigIntegerField(),
        ),
        analysis_video_count=Count("id"),
    )

    latest_video = videos.order_by("-created_at").first()

    latest_analysis = None
    if latest_video:
        latest_analysis = {
            "videoId": latest_video.id,
            "title": latest_video.title,
            "weather": latest_video.weather,
            "fishCount": latest_video.fish_count,
            "skygazerCount": latest_video.skygazer_count,
            "analyzedAt": format_date(latest_video.created_at),
            "createdAt": timezone.localtime(latest_video.created_at).strftime(
                "%Y-%m-%d %H:%M"
            ),
        }

    return {
        "id": region.id,
        "regionName": region.region_name,
        "latitude": to_float(region.latitude),
        "longitude": to_float(region.longitude),
        "gps": f"{region.latitude}, {region.longitude}",
        "riskLevel": region.risk_level,
        "riskLabel": get_risk_label(region.risk_level),
        "managementStatus": get_management_status(region.risk_level),
        "totalDetected": aggregate["total_detected"],
        "totalFish": aggregate["total_fish"],
        "analysisVideoCount": aggregate["analysis_video_count"],
        "latestAnalysis": latest_analysis,
    }


def get_top_regions(limit=3):
    rows = (
        completed_videos()
        .values(
            "region_id",
            "region__region_name",
            "region__risk_level",
        )
        .annotate(
            detected_count=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
        .order_by("-detected_count")[:limit]
    )

    result = []

    for index, row in enumerate(rows, start=1):
        result.append(
            {
                "rank": index,
                "regionId": row["region_id"],
                "regionName": row["region__region_name"],
                "detectedCount": row["detected_count"],
                "riskLevel": row["region__risk_level"],
                "riskLabel": get_risk_label(row["region__risk_level"]),
            }
        )

    return result


def build_event_message(video):
    count = video.skygazer_count or 0
    risk_level = video.region.risk_level

    if count == 0:
        return "강준치 탐지 없음"

    if risk_level == "HIGH":
        return f"강준치 {count}마리 탐지 - 집중 모니터링 필요"

    return f"강준치 {count}마리 탐지"


def get_recent_analysis_events(limit=4):
    videos = completed_videos().order_by("-created_at")[:limit]

    events = []

    for video in videos:
        events.append(
            {
                "id": video.id,
                "videoId": video.id,
                "date": format_short_date(video.created_at),
                "time": format_time(video.created_at),
                "regionId": video.region_id,
                "regionName": video.region.region_name,
                "detectedCount": video.skygazer_count,
                "riskLevel": video.region.risk_level,
                "riskLabel": get_risk_label(video.region.risk_level),
                "message": build_event_message(video),
            }
        )

    return events


def get_dashboard_overview():
    today = timezone.localdate()

    recent_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    previous_end = today - timedelta(days=7)

    recent_7days_detected = completed_videos().filter(
        created_at__date__gte=recent_start,
        created_at__date__lte=today,
    ).aggregate(
        total=Coalesce(
            Sum("skygazer_count"),
            Value(0),
            output_field=BigIntegerField(),
        )
    )["total"]

    previous_7days_detected = completed_videos().filter(
        created_at__date__gte=previous_start,
        created_at__date__lte=previous_end,
    ).aggregate(
        total=Coalesce(
            Sum("skygazer_count"),
            Value(0),
            output_field=BigIntegerField(),
        )
    )["total"]

    return {
        "totalRegions": Region.objects.count(),
        "normalRegions": Region.objects.filter(risk_level="LOW").count(),
        "warningRegions": Region.objects.filter(risk_level="MEDIUM").count(),
        "dangerRegions": Region.objects.filter(risk_level="HIGH").count(),
        "recent7DaysDetected": recent_7days_detected,
        "recent7DaysChange": recent_7days_detected - previous_7days_detected,
    }


def get_dashboard_summary():
    return {
        "overview": get_dashboard_overview(),
        "recentAnalysisEvents": get_recent_analysis_events(),
        "topRegions": get_top_regions(),
    }


def get_dashboard_home(risk="ALL"):
    return {
        "markers": get_dashboard_markers(risk=risk),
        "summary": get_dashboard_summary(),
    }
