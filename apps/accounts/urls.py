from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("recommendations/", views.recommendation_history, name="recommendation_history"),
    path(
        "recommendations/<uuid:session_key>/",
        views.recommendation_history_detail,
        name="recommendation_history_detail",
    ),
]
