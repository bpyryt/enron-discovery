from django.urls import path

from .views import (
    conversation_detail,
    conversation_list,
    dashboard,
    home,
    message_detail,
    message_list,
)

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("messages/", message_list, name="message_list"),
    path("messages/<int:pk>/", message_detail, name="message_detail"),
    path("conversations/", conversation_list, name="conversation_list"),
    path("conversation/", conversation_detail, name="conversation_detail"),
]