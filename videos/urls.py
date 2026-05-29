from django.urls import path
from .views import VideoUploadView

urlpatterns = [
    path("", VideoListDeleteView.as_view(), name="video-list-delete"),
    path("regions/", VideoRegionListView.as_view(), name="video-regions"),
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
]
