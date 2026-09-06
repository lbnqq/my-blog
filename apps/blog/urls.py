from django.urls import path

from . import views


app_name = "blog"

urlpatterns = [
    path("", views.home, name="home"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),
    path("douban-chart/<str:douban_id>/", views.douban_chart_detail, name="douban_chart_detail"),
    path(
        "douban-weekly-reputation/<str:douban_id>/",
        views.douban_weekly_reputation_detail,
        name="douban_weekly_reputation_detail",
    ),
    path("douban-chart/poster/<str:douban_id>/", views.douban_chart_poster, name="douban_chart_poster"),
    path(
        "douban-weekly-reputation/poster/<str:douban_id>/",
        views.douban_weekly_reputation_poster,
        name="douban_weekly_reputation_poster",
    ),
]
