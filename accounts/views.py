from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import User
from analysis.models import Event
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework.permissions import AllowAny


# 회원가입
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    user_id = request.data.get("user_id")
    password = request.data.get("password")
    username = request.data.get("username")  # 유저 이름

    if not user_id or not password or not username:
        return Response(
            {"message": "입력값을 확인해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(user_id=user_id).exists():
        return Response(
            {"message": "이미 사용 중인 아이디입니다."},
            status=status.HTTP_409_CONFLICT
        )

    user = User(
        user_id=user_id,
        username=username,
    )
    user.set_password(password)
    user.save()

    return Response(status=status.HTTP_201_CREATED)


# 로그인
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    user_id = request.data.get("user_id")
    password = request.data.get("password")

    try:
        user = User.objects.get(user_id=user_id)
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

    payload = {
        "id": user.id,
        "user_id": user.user_id,
        "username": user.username,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    Event.objects.create(
        user=None,
        type=Event.Type.LOGIN,
        detail=f"{user.username} 로그인"
    )

    return Response({
        "token": token,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
        }
    }, status=status.HTTP_200_OK)


# 아이디 중복 체크
@api_view(['GET'])
@permission_classes([AllowAny])
def check_username(request):
    user_id = request.GET.get("user_id", "").strip()

    if not user_id:
        return Response(
            {"message": "입력값을 확인해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    exists = User.objects.filter(user_id=user_id).exists()

    return Response(
        {"available": not exists},
        status=status.HTTP_200_OK
    )


# 로그아웃
@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    auth = request.headers.get("Authorization", "")
    username = ""
    if auth.startswith("Bearer "):
        try:
            payload = jwt.decode(auth.split(" ")[1], settings.SECRET_KEY, algorithms=["HS256"])
            username = payload.get("username", "")
        except jwt.PyJWTError:
            pass

    if username:
        Event.objects.create(
            user=None,
            type=Event.Type.LOGOUT,
            detail=f"{username} 로그아웃"
        )
    return Response(status=status.HTTP_200_OK)
