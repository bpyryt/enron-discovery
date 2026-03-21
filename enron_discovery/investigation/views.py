from django.shortcuts import render, get_object_or_404
from .models import Message


def message_list(request):
    messages = (
        Message.objects
        .select_related("sender")
        .order_by("-id")[:100]
    )
    return render(request, "investigation/message_list.html", {"messages": messages})


def message_detail(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("sender").prefetch_related("recipients__employee", "replies__sender"),
        id=message_id
    )
    return render(request, "investigation/message_detail.html", {"message": message})