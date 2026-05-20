from django.urls import path
from .views import ping
from . import views

urlpatterns = [
    path("ping/", ping),

    # auth
    path('auth/login/', views.login),
    path('auth/register/', views.signup),
    path('auth/check-id/', views.check_username),

    # videos
    path('videos', views.video_list),
    path('videos/delete', views.video_delete),
    path('videos/<int:video_id>/', views.video_detail),

    # logs
    path('logs/', views.log_list),

    # basins
    path('basins', views.basin_list),
    path('basins/create', views.create_basin),
    path('basins/<int:basin_id>', views.basin_detail),
    path('basins/<int:basin_id>/update', views.update_basin),
    path('basins/<int:basin_id>/delete', views.delete_basin),
]