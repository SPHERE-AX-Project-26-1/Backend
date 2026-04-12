from django.urls import path
from .views import ping
from . import views

urlpatterns = [
    path("ping/", ping),
]

urlpatterns = [
    path('videos', views.video_list),
    path('videos/delete', views.video_delete),
    path('videos/<int:video_id>', views.video_detail),
    path('logs', views.log_list),
    path('basins', views.basin_list),
    path('basins/create', views.create_basin),
    path('basins/<int:basin_id>', views.basin_detail),
    path('basins/<int:basin_id>/update', views.update_basin),
    path('basins/<int:basin_id>/delete', views.delete_basin),
]