from django.urls import path
from .views import ping
from . import views

urlpatterns = [
    path("ping/", ping),
    
    # videos
    path('videos', views.video_list),
    path('videos/delete', views.video_delete),
    path('videos/<int:video_id>/', views.video_detail),

    # logs
    path('logs/', views.log_list),

]
