from django.urls import path

from .views import dashboard, message_detail, message_list

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("messages/", message_list, name="message_list"),
    path("messages/<int:pk>/", message_detail, name="message_detail"),
]