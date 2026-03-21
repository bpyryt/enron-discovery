from django.shortcuts import render, get_object_or_404
from .models import Message


def message_list(request):
    messages = Message.objects.all().order_by("-id")[:100]
    return render(request, "investigation/message_list.html", {"messages": messages})


def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    return render(request, "investigation/message_detail.html", {"message": message})