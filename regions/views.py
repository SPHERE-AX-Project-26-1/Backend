from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Region

@api_view(['POST'])
def create_region(request):
    data = request.data

    region = Region.objects.create(
        name=data.get('name'),
        address=data.get('address'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        risk_level=data.get('risk_level', 'LOW')
    )

    return Response({"id": region.id})

@api_view(['GET'])
def region_list(request):
    regions = Region.objects.all()

    # 검색
    name = request.GET.get('name')
    address = request.GET.get('address')

    if name:
        regions = regions.filter(name__icontains=name)
    if address:
        regions = regions.filter(address__icontains=address)

    # 정렬
    sort = request.GET.get('sort')
    if sort == 'latest':
        regions = regions.order_by('-created_at')

    data = [
        {
            "id": r.id,
            "name": r.name,
            "address": r.address,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "risk_level": r.risk_level
        }
        for r in regions
    ]

    return Response({"regions": data})

@api_view(['GET'])
def region_detail(request, region_id):
    region = Region.objects.get(id=region_id)

    return Response({
        "id": region.id,
        "name": region.name,
        "address": region.address,
        "latitude": region.latitude,
        "longitude": region.longitude,
        "risk_level": region.risk_level
    })

@api_view(['PUT'])
def update_region(request, region_id):
    region = Region.objects.get(id=region_id)
    data = request.data

    region.name = data.get('name', region.name)
    region.address = data.get('address', region.address)
    region.latitude = data.get('latitude', region.latitude)
    region.longitude = data.get('longitude', region.longitude)
    region.risk_level = data.get('risk_level', region.risk_level)

    region.save()

    return Response({"success": True})

@api_view(['DELETE'])
def delete_region(request, region_id):
    region = Region.objects.get(id=region_id)
    region.delete()

    return Response({"success": True})
