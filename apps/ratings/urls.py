from django.urls import path

from . import views


app_name = "ratings"

urlpatterns = [
    path("category/", views.select_category, name="category"),
    path("rate/<uuid:session_key>/", views.rate_movies, name="rate"),
    path("result/<uuid:session_key>/", views.recommendation_result, name="result"),
]
