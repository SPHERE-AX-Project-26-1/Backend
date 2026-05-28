from django.contrib import admin
from django.urls import path, include
from analysis.views import ping
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/ping/', ping),
    path('api/token/refresh/', TokenRefreshView.as_view()),  # refresh 토큰으로 access 재발급
    path('api/', include('analysis.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/basins/', include('regions.urls')),
]