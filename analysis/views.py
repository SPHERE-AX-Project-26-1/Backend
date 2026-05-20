from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Video
from .models import Basin 
from .models import SystemLog
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg
from django.utils import timezone

# 테스트용 ping
@api_view(['GET'])
def ping(request):
    return Response({"message": "pong"})


# 회원가입
@api_view(['POST'])
def signup(request):
    user_id = request.data.get("userId")
    password = request.data.get("password")
    name = request.data.get("name", "")
    email = request.data.get("email", "")

    if not user_id or not password or not name or not email:
        return Response(
            {"message": "입력값을 확인해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=user_id).exists():
        return Response(
            {"message": "이미 사용 중인 아이디입니다."},
            status=status.HTTP_409_CONFLICT
        )

    User.objects.create_user(
        username=user_id,
        password=password,
        email=email,
        first_name=name,
    )

    return Response(status=status.HTTP_201_CREATED)


# 로그인
@api_view(['POST'])
def login(request):
    user_id = request.data.get("userId")
    password = request.data.get("password")

    try:
        user = User.objects.get(username=user_id)
    except User.DoesNotExist:
        return Response(
            {"message": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {"message": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "token": str(refresh.access_token),
        "user": {
            "userId": user.username,
            "name": user.first_name,
            "email": user.email
        }
    }, status=status.HTTP_200_OK)


# 아이디 중복 체크
@api_view(['GET'])
def check_username(request):
    user_id = request.GET.get("userId", "").strip()

    if not user_id:
        return Response(
            {"message": "입력값을 확인해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    exists = User.objects.filter(username=user_id).exists()

    return Response(
        {"available": not exists},
        status=status.HTTP_200_OK
    )



def video_list(request):
    videos = Video.objects.all()

    region = request.GET.get('region')
    keyword = request.GET.get('keyword')

    if region:
        videos = videos.filter(region=region)

    if keyword:
        videos = videos.filter(filename__icontains=keyword)

    sort = request.GET.get('sort', 'date')
    if sort == 'date':
        videos = videos.order_by('-date')
    elif sort == 'region':
        videos = videos.order_by('region')

    page = int(request.GET.get('page', 1))
    size = int(request.GET.get('size', 10))

    paginator = Paginator(videos, size)
    page_obj = paginator.get_page(page)

    data = []
    for v in page_obj:
        data.append({
            "id": v.id,
            "filename": v.filename,
            "thumbnail": v.thumbnail.url if v.thumbnail else None,
            "date": v.date,
            "region": v.region,
            "fish_count": v.fish_count,
            "total_count": v.total_count,
            "severity": "HIGH" if v.fish_count >= 10 else "LOW"
        })

    return JsonResponse({
        "videos": data,
        "total_pages": paginator.num_pages
    })


@csrf_exempt
def video_delete(request):
    if request.method == "DELETE":
        body = json.loads(request.body)
        ids = body.get("video_ids", [])

        Video.objects.filter(id__in=ids).delete()
        
        SystemLog.objects.create(
            event_type="DELETE_VIDEO",
            message="영상 삭제됨",
            user_id=1
        )

        return JsonResponse({"success": True})

def video_detail(request, video_id):
    try:
        v = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return JsonResponse({"message": "존재하지 않는 영상입니다."}, status=404)

    region_avg = Video.objects.filter(region=v.region).aggregate(
        avg=Avg("fish_count")
    )["avg"] or 0

    year_avg = Video.objects.filter(date__year=timezone.now().year).aggregate(
        avg=Avg("fish_count")
    )["avg"] or 0

    return JsonResponse({
        "id": v.id,
        "filename": v.filename,
        "date": str(v.date),
        "uploadTime": str(v.date),
        "region": v.region,
        "location": getattr(v, "location", ""),
        "gps": getattr(v, "gps", ""),
        "ganjunchiCount": v.fish_count,
        "totalCount": v.total_count,
        "weather": getattr(v, "weather", ""),
        "duration": getattr(v, "duration", ""),
        "detectionRanges": [],
        "regionAvg": int(region_avg),
        "yearAvg": int(year_avg),
        "uploader": getattr(v, "uploader", "")
    })

def log_list(request):
    logs = SystemLog.objects.all().order_by('-created_at')

    data = []

    for log in logs:
        data.append({
            "id": log.id,
            "datetime": log.created_at.strftime("%Y-%m-%d %H:%M"),
            "eventType": log.event_type,
            "detail": log.message,
            "user": "시스템"
        })

    return JsonResponse({
        "items": data
    })

@api_view(['POST'])
def create_basin(request):
    data = request.data

    basin = Basin.objects.create(
        name=data.get('name'),
        region=data.get('region'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        severity=data.get('severity', 'LOW')
    )

    return Response({"id": basin.id})

@api_view(['GET'])
def basin_list(request):
    basins = Basin.objects.all()

    # 검색
    name = request.GET.get('name')
    region = request.GET.get('region')

    if name:
        basins = basins.filter(name__icontains=name)
    if region:
        basins = basins.filter(region__icontains=region)

    # 정렬
    sort = request.GET.get('sort')
    if sort == 'latest':
        basins = basins.order_by('-created_at')

    data = [
        {
            "id": b.id,
            "name": b.name,
            "region": b.region,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "severity": b.severity
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
        "region": basin.region,
        "latitude": basin.latitude,
        "longitude": basin.longitude,
        "severity": basin.severity
    })

@api_view(['PUT'])
def update_basin(request, basin_id):
    basin = Basin.objects.get(id=basin_id)
    data = request.data

    basin.name = data.get('name', basin.name)
    basin.region = data.get('region', basin.region)
    basin.latitude = data.get('latitude', basin.latitude)
    basin.longitude = data.get('longitude', basin.longitude)
    basin.severity = data.get('severity', basin.severity)

    basin.save()

    return Response({"success": True})

@api_view(['DELETE'])
def delete_basin(request, basin_id):
    basin = Basin.objects.get(id=basin_id)
    basin.delete()

    return Response({"success": True})