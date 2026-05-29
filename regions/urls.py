from django.urls import path
from . import views

urlpatterns = [
    path('', views.basin_list),
    path('create', views.create_basin),
    path('<int:basin_id>', views.basin_detail),
    path('<int:basin_id>/update', views.update_basin),
    path('<int:basin_id>/delete', views.delete_basin),
]
