from django.urls import path

from . import views


app_name = "recommendations"

urlpatterns = [
    path("", views.analytics_center, name="center"),
    path("recommendations/", views.recommendation_analytics, name="analytics"),
    path("users/", views.user_analytics, name="user_analytics"),
    path("movies/", views.movie_analytics, name="movie_analytics"),
    path("data-quality/", views.data_quality, name="data_quality"),
    path("data-quality/sync/<str:source>/", views.sync_data, name="sync_data"),
    path("data-quality/sync-all/", views.sync_all, name="sync_all"),
]
