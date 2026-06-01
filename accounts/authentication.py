from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
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

        return JWTAuthentication().authenticate(request)
