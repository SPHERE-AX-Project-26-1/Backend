from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login),
    path('register', views.signup),
    path('check-id', views.check_username),
    path('logout', views.logout),
]
