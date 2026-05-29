from django.contrib import admin
from django.urls import path, include
from analysis.views import ping
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/ping/', ping),
    path('api/token/refresh/', TokenRefreshView.as_view()),  # refresh 토큰으로 access 재발급
    path('api/', include('analysis.urls')),
    path("api/videos/", include('videos.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/rivers/', include('regions.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
