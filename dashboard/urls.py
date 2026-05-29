from django.urls import path


from .views import (
    DashboardSummaryAPIView,
    DashboardRiversAPIView,
    DashboardTopRiversAPIView,
)


urlpatterns = [
    path("summary/", DashboardSummaryAPIView.as_view(), name="dashboard-summary"),
    path("rivers/", DashboardRiversAPIView.as_view(), name="dashboard-rivers"),
    path("top-rivers/", DashboardTopRiversAPIView.as_view(), name="dashboard-top-rivers"),
]
