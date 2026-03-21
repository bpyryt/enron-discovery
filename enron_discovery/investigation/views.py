from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Employee, Message


def message_list(request):
    q = request.GET.get("q", "").strip()
    sender = request.GET.get("sender", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

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

    if sender:
        messages = messages.filter(sender__email__icontains=sender)

    if date_from:
        messages = messages.filter(sent_at__date__gte=date_from)

    if date_to:
        messages = messages.filter(sent_at__date__lte=date_to)

    senders = Employee.objects.order_by("email")
    result_count = messages.count()

    context = {
        "messages": messages,
        "senders": senders,
        "q": q,
        "sender": sender,
        "date_from": date_from,
        "date_to": date_to,
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