from django.urls import path

from . import views


app_name = "recommendations"

urlpatterns = [
    path("recommendations/", views.recommendation_analytics, name="analytics"),
]
