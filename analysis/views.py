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

# 테스트용 ping
@api_view(['GET'])
def ping(request):
    return Response({"message": "pong"})


# 회원가입
@api_view(['POST'])
def signup(request):
    username = request.data.get("username")
    password = request.data.get("password")
    password2 = request.data.get("password2")
    name = request.data.get("name", "")
    email = request.data.get("email", "")

    # 필수 필드 검증
    if not username or not password:
        return Response(
            {"success": False, "message": "아이디와 비밀번호는 필수입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 비밀번호 확인
    if password != password2:
        return Response(
            {"success": False, "message": "비밀번호가 일치하지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 아이디 중복 체크
    if User.objects.filter(username=username).exists():
        return Response(
            {"success": False, "message": "이미 사용 중인 아이디입니다."},
            status=status.HTTP_409_CONFLICT
        )

    # 유저 생성
    User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=name,
    )

    return Response(
        {"success": True, "message": "회원가입이 완료되었습니다."},
        status=status.HTTP_201_CREATED
    )


# 로그인
@api_view(['POST'])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {"success": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {"success": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # simplejwt access / refresh 토큰 발급
    refresh = RefreshToken.for_user(user)

    return Response({
        "success": True,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }, status=status.HTTP_200_OK)


# 아이디 중복 체크
@api_view(['GET'])
def check_username(request):
    username = request.GET.get("username", "").strip()

    if not username:
        return Response(
            {"success": False, "message": "아이디를 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    is_duplicate = User.objects.filter(username=username).exists()

    return Response(
        {"is_duplicate": is_duplicate},
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
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse({
        "id": v.id,
        "filename": v.filename,
        "video_url": v.file.url,
        "date": v.date,
        "region": v.region,
        "fish_count": v.fish_count,
        "total_count": v.total_count,
        "other_count": v.total_count - v.fish_count,
        "timestamps": [],
        "avg_region": 0,
        "avg_year": 0
    })

def log_list(request):
    logs = SystemLog.objects.all().order_by('-created_at')

    page = int(request.GET.get('page', 1))
    size = int(request.GET.get('size', 10))

    paginator = Paginator(logs, size)
    page_obj = paginator.get_page(page)

    data = []
    for log in page_obj:
        data.append({
            "id": log.id,
            "event_type": log.event_type,
            "message": log.message,
            "user_id": log.user_id,
            "created_at": log.created_at,
        })

    return JsonResponse({
        "logs": data,
        "total_pages": paginator.num_pages
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