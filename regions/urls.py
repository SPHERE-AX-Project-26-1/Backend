from django.urls import path
from . import views

urlpatterns = [
    path('', views.region_list),
    path('create', views.create_region),
    path('<int:region_id>', views.region_detail),
    path('<int:region_id>/update', views.update_region),
    path('<int:region_id>/delete', views.delete_region),
]
