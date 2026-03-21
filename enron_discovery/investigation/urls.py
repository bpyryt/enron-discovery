from django.urls import path

from .views import message_list, message_detail

urlpatterns = [
    path("", message_list, name="message_list"),
    path("<int:pk>/", message_detail, name="message_detail"),
]