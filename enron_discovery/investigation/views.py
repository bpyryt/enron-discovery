from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Message


def message_list(request):
    q = request.GET.get("q", "").strip()

    messages = (
        Message.objects
        .select_related("sender")
        .order_by("-sent_at", "-id")
    )

    if q:
        messages = messages.filter(
            Q(subject__icontains=q) |
            Q(body_text__icontains=q) |
            Q(body_clean__icontains=q) |
            Q(sender__email__icontains=q)
        )

    result_count = messages.count()

    context = {
        "messages": messages,
        "q": q,
        "result_count": result_count,
    }
    return render(request, "investigation/message_list.html", context)


def message_detail(request, pk):
    message = get_object_or_404(
        Message.objects.select_related("sender").prefetch_related(
            "recipients",
            "replies",
        ),
        pk=pk,
    )

    context = {
        "message": message,
    }
    return render(request, "investigation/message_detail.html", context)