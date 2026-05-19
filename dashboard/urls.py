from django.urls import path
from .views import (
    DashboardHomeAPIView,
    DashboardMapAPIView,
    DashboardRegionDetailAPIView,
    DashboardSummaryAPIView,
)

urlpatterns = [
    path("", DashboardHomeAPIView.as_view()),
    path("map/", DashboardMapAPIView.as_view()),
    path("regions/<int:region_id>/", DashboardRegionDetailAPIView.as_view()),
    path("summary/", DashboardSummaryAPIView.as_view()),
]
