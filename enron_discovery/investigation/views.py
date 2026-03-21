from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, render

from .models import Employee, Message


def home(request):
    return render(request, "investigation/home.html")


def message_list(request):
    q = request.GET.get("q", "").strip()
    sender = request.GET.get("sender", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    messages = Message.objects.select_related("sender")

    if q:
        search_vector = (
            SearchVector("subject", weight="A") +
            SearchVector("body_clean", weight="B") +
            SearchVector("body_text", weight="C")
        )
        search_query = SearchQuery(q)

        messages = (
            messages
            .annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gt=0)
        )

    if sender:
        messages = messages.filter(sender__email__icontains=sender)

    if date_from:
        messages = messages.filter(sent_at__date__gte=date_from)

    if date_to:
        messages = messages.filter(sent_at__date__lte=date_to)

    if q:
        messages = messages.order_by("-rank", "-sent_at", "-id")
    else:
        messages = messages.order_by("-sent_at", "-id")

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


def dashboard(request):
    total_messages = Message.objects.count()
    total_senders = Employee.objects.count()

    messages_with_date = Message.objects.exclude(sent_at__isnull=True)

    messages_by_month = (
        messages_with_date
        .annotate(month=TruncMonth("sent_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    top_senders = (
        Employee.objects
        .annotate(message_count=Count("sent_messages"))
        .filter(message_count__gt=0)
        .order_by("-message_count", "email")[:10]
    )

    context = {
        "total_messages": total_messages,
        "total_senders": total_senders,
        "messages_by_month": messages_by_month,
        "top_senders": top_senders,
    }
    return render(request, "investigation/dashboard.html", context)