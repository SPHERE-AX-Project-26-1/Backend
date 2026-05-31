import pandas as pd
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
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


def region_response(r):
    return {
        "id": r.id,
        "name": r.name,
        "region": r.address,
        "latitude": float(r.latitude),
        "longitude": float(r.longitude),
        "risk": risk_to_api(r.risk_level),
        "lastAnalyzedAt": None,
        "cautionThreshold": r.caution_threshold,
        "dangerThreshold": r.danger_threshold,
        "createdAt": r.created_at.strftime("%Y-%m-%d") if r.created_at else None,
        "analysisCount": 0,
        "totalGanjunchiCount": 0,
        "latestGanjunchiCount": 0,
    }


@api_view(['GET', 'POST'])
def regions(request):
    if request.method == 'POST':
        data = request.data

        region = Region.objects.create(
            name=data.get("name"),
            address=data.get("region"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            caution_threshold=data.get("cautionThreshold", 5),
            danger_threshold=data.get("dangerThreshold", 10),
            risk_level=risk_to_db(data.get("risk", "LOW")),
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
        region.address = data.get("region", region.address)
        region.latitude = data.get("latitude", region.latitude)
        region.longitude = data.get("longitude", region.longitude)
        region.caution_threshold = data.get("cautionThreshold", region.caution_threshold)
        region.danger_threshold = data.get("dangerThreshold", region.danger_threshold)

        if data.get("risk"):
            region.risk_level = risk_to_db(data.get("risk"))

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
        "region",
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
                address=row["region"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                caution_threshold=row["cautionThreshold"],
                danger_threshold=row["dangerThreshold"],
                risk_level="LOW",
            )

            created_items.append({
                "id": region.id,
                "name": region.name,
                "region": region.address,
            })

        except Exception:
            failed_count += 1

    return Response({
        "createdCount": len(created_items),
        "failedCount": failed_count,
        "items": created_items
    })