from django.urls import path
from .views import (
    TotalDetectedAPIView,
    TotalVideosAPIView,
    TopRegionAPIView,
    TopWeatherAPIView,
    MonthlyStatsAPIView,
    ByRegionStatsAPIView,
    ByWeatherStatsAPIView,
)

urlpatterns = [
    path("total-detected/", TotalDetectedAPIView.as_view()),
    path("total-videos/", TotalVideosAPIView.as_view()),
    path("top-region/", TopRegionAPIView.as_view()),
    path("top-weather/", TopWeatherAPIView.as_view()),
    path("monthly/", MonthlyStatsAPIView.as_view()),
    path("by-region/", ByRegionStatsAPIView.as_view()),
    path("by-weather/", ByWeatherStatsAPIView.as_view()),
]
