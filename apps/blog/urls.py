from django.urls import path

from . import views


app_name = "blog"

urlpatterns = [
    path("", views.home, name="home"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),
]
