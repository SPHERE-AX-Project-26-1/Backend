from django.urls import path
from . import views

urlpatterns = [
    path('', views.regions),
    path('upload', views.upload_regions),
    path('<int:region_id>', views.region),
]