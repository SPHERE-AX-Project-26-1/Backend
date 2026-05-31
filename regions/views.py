import pandas as pd
from django.db.models import Q, Sum
from videos.models import Video
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Region


def risk_to_db(value):
    return {
        "보통": "LOW",
        "주의": "MEDIUM",
        "위험": "HIGH",
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
    }.get(value, value)


def risk_to_api(value):
    return {
        "LOW": "보통",
        "MEDIUM": "주의",
        "HIGH": "위험",
    }.get(value, value)


def calculate_risk(region, latest_count):
    if latest_count >= region.danger_threshold:
        return "HIGH"
    elif latest_count >= region.caution_threshold:
        return "MEDIUM"
    return "LOW"


def region_response(r):
    videos = Video.objects.filter(region=r, status=Video.Status.COMPLETED)

    analysis_count = videos.count()
    total_skygazer_count = videos.aggregate(total=Sum("skygazer_count"))["total"] or 0

    latest_video = videos.order_by("-date", "-created_at").first()
    latest_skygazer_count = latest_video.skygazer_count if latest_video else 0

    calculated_risk = calculate_risk(r, latest_skygazer_count)

    return {
        "id": r.id,
        "name": r.name,
        "address": r.address,
        "latitude": float(r.latitude),
        "longitude": float(r.longitude),
        "risk": risk_to_api(calculated_risk),
        "lastAnalyzedAt": latest_video.created_at.strftime("%Y-%m-%d %H:%M") if latest_video else None,
        "cautionThreshold": r.caution_threshold,
        "dangerThreshold": r.danger_threshold,
        "createdAt": r.created_at.strftime("%Y-%m-%d") if r.created_at else None,
        "analysisCount": analysis_count,
        "totalGanjunchiCount": total_skygazer_count,
        "latestGanjunchiCount": latest_skygazer_count,
    }


@api_view(['GET', 'POST'])
def regions(request):
    if request.method == 'POST':
        data = request.data

        region = Region.objects.create(
            name=data.get("name"),
            address=data.get("address"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            caution_threshold=data.get("cautionThreshold", 5),
            danger_threshold=data.get("dangerThreshold", 10),
            risk_leve="LOW",
            # risk_level=risk_to_db(data.get("risk", "LOW")),
        )

        return Response(region_response(region))

    regions = Region.objects.all()

    search = request.GET.get("search")
    risk = request.GET.get("risk")
    sort_by = request.GET.get("sortBy")

    if search:
        regions = regions.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search)
        )

    if risk:
        regions = regions.filter(risk_level=risk_to_db(risk))

    if sort_by == "recent":
        regions = regions.order_by("-updated_at")
    elif sort_by == "name":
        regions = regions.order_by("name")
    elif sort_by == "risk":
        regions = regions.order_by("-risk_level")
    elif sort_by == "count":
        regions = regions.order_by("-id")

    return Response({
        "items": [region_response(r) for r in regions]
    })


@api_view(['GET', 'PUT', 'DELETE'])
def region(request, region_id):
    region = Region.objects.get(id=region_id)

    if request.method == 'GET':
        return Response(region_response(region))

    if request.method == 'PUT':
        data = request.data

        region.name = data.get("name", region.name)
        region.address = data.get("address", region.address)
        region.latitude = data.get("latitude", region.latitude)
        region.longitude = data.get("longitude", region.longitude)
        region.caution_threshold = data.get("cautionThreshold", region.caution_threshold)
        region.danger_threshold = data.get("dangerThreshold", region.danger_threshold)

        region.save()

        return Response(region_response(region))

    if request.method == 'DELETE':
        region.delete()
        return Response({
            "message": "유역이 삭제되었습니다."
        })


@api_view(['POST'])
def upload_regions(request):
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return Response({"message": "파일을 첨부해주세요."}, status=400)

    filename = uploaded_file.name.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            return Response({"message": "지원하지 않는 파일 형식입니다."}, status=400)
    except Exception:
        return Response({"message": "파일을 읽는 중 오류가 발생했습니다."}, status=400)

    required_columns = [
        "name",
        "address",
        "latitude",
        "longitude",
        "cautionThreshold",
        "dangerThreshold",
    ]

    for col in required_columns:
        if col not in df.columns:
            return Response({"message": f"{col} 컬럼이 필요합니다."}, status=400)

    created_items = []
    failed_count = 0

    for _, row in df.iterrows():
        try:
            region = Region.objects.create(
                name=row["name"],
                address=row["address"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                caution_threshold=row["cautionThreshold"],
                danger_threshold=row["dangerThreshold"],
                risk_level="LOW",
            )

            created_items.append({
                "id": region.id,
                "name": region.name,
                "address": region.address,
            })

        except Exception:
            failed_count += 1

    return Response({
        "createdCount": len(created_items),
        "failedCount": failed_count,
        "items": created_items
    })
