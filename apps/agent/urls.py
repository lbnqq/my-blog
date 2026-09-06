from django.urls import path

from . import views


app_name = "agent"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("confirm-action/", views.confirm_action, name="confirm_action"),
    path("feishu/events/", views.feishu_events, name="feishu_events"),
]
