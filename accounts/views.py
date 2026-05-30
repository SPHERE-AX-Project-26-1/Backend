from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# 회원가입
@api_view(['POST'])
def signup(request):
    user_id = request.data.get("userId")
    password = request.data.get("password")
    name = request.data.get("name", "")

    if not user_id or not password or not name:
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

