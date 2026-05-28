from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Basin

@api_view(['POST'])
def create_basin(request):
    data = request.data

    basin = Basin.objects.create(
        name=data.get('name'),
        address=data.get('address'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        risk_level=data.get('risk_level', 'LOW')
    )

    return Response({"id": basin.id})

@api_view(['GET'])
def basin_list(request):
    basins = Basin.objects.all()

    # 검색
    name = request.GET.get('name')
    address = request.GET.get('address')

    if name:
        basins = basins.filter(name__icontains=name)
    if address:
        basins = basins.filter(address__icontains=address)

    # 정렬
    sort = request.GET.get('sort')
    if sort == 'latest':
        basins = basins.order_by('-created_at')

    data = [
        {
            "id": b.id,
            "name": b.name,
            "address": b.address,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "risk_level": b.risk_level
        }
        for b in basins
    ]

    return Response({"basins": data})

@api_view(['GET'])
def basin_detail(request, basin_id):
    basin = Basin.objects.get(id=basin_id)

    return Response({
        "id": basin.id,
        "name": basin.name,
        "address": basin.address,
        "latitude": basin.latitude,
        "longitude": basin.longitude,
        "risk_level": basin.risk_level
    })

@api_view(['PUT'])
def update_basin(request, basin_id):
    basin = Basin.objects.get(id=basin_id)
    data = request.data

    basin.name = data.get('name', basin.name)
    basin.address = data.get('address', basin.address)
    basin.latitude = data.get('latitude', basin.latitude)
    basin.longitude = data.get('longitude', basin.longitude)
    basin.risk_level = data.get('risk_level', basin.risk_level)

    basin.save()

    return Response({"success": True})

@api_view(['DELETE'])
def delete_basin(request, basin_id):
    basin = Basin.objects.get(id=basin_id)
    basin.delete()

    return Response({"success": True})