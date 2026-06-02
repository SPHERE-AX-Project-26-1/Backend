import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import User


class DevJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if getattr(settings, "APP_ENV", "prod") == "dev":
            try:
                user = User.objects.get(pk=1)
            except User.DoesNotExist:
                raise AuthenticationFailed("테스트 유저(id=1)가 존재하지 않습니다.")

            return (user, None)

        auth = request.headers.get("Authorization", "")

        if not auth.startswith("Bearer "):
            return None

        token = auth.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("토큰이 만료되었습니다.")
        except jwt.PyJWTError:
            raise AuthenticationFailed("유효하지 않은 토큰입니다.")

        user_id = payload.get("id")

        if not user_id:
            raise AuthenticationFailed("토큰에 사용자 정보가 없습니다.")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed("사용자를 찾을 수 없습니다.")

        return (user, token)