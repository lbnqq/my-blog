from django.urls import path

from . import views


app_name = "movies"

urlpatterns = [
    path("<int:pk>/", views.movie_detail, name="detail"),
]
