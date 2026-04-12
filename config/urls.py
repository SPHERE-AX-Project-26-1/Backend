from django.contrib import admin
from django.urls import path, include
from analysis.views import ping, signup, login, check_username
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/ping/', ping),
    path('api/signup/', signup),
    path('api/login/', login),
    path('api/check-username/', check_username),
    path('api/token/refresh/', TokenRefreshView.as_view()),  # refresh 토큰으로 access 재발급
    path('api/', include('analysis.urls')),
]