from django.urls import path
from .views import VideoDetailView, VideoUploadView, VideoListDeleteView, VideoRegionListView

urlpatterns = [
    path("", VideoListDeleteView.as_view(), name="video-list-delete"),
    path("regions", VideoRegionListView.as_view(), name="video-regions"),
    path("upload", VideoUploadView.as_view(), name="video-upload"),
    path("<int:video_id>", VideoDetailView.as_view(), name="video-detail"),
]
