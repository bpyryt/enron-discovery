import re
from collections import Counter

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, render

from .models import Employee, Message


SUBJECT_PREFIX_RE = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.IGNORECASE)


def normalize_subject(subject):
    if not subject:
        return ""

    normalized = subject.strip()

    previous = None
    while previous != normalized:
        previous = normalized
        normalized = SUBJECT_PREFIX_RE.sub("", normalized).strip()

    return normalized.lower()


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

    normalized_subject = normalize_subject(message.subject)

    conversation_messages = []
    if normalized_subject:
        candidate_messages = (
            Message.objects.select_related("sender")
            .filter(subject__isnull=False)
            .exclude(subject="")
            .order_by("sent_at", "id")
        )

        conversation_messages = [
            candidate
            for candidate in candidate_messages
            if normalize_subject(candidate.subject) == normalized_subject
        ]

    context = {
        "message": message,
        "normalized_subject": normalized_subject,
        "conversation_messages": conversation_messages,
    }
    return render(request, "investigation/message_detail.html", context)


def conversation_list(request):
    messages = Message.objects.exclude(subject__isnull=True).exclude(subject="")

    normalized_subjects = []
    for message in messages:
        normalized = normalize_subject(message.subject)
        if normalized:
            normalized_subjects.append(normalized)

    counts = Counter(normalized_subjects)

    conversations = [
        {"subject": subject, "count": count}
        for subject, count in counts.items()
        if count > 1
    ]
    conversations.sort(key=lambda item: (-item["count"], item["subject"]))

    context = {
        "conversations": conversations,
        "conversation_count": len(conversations),
    }
    return render(request, "investigation/conversation_list.html", context)


def conversation_detail(request):
    subject = request.GET.get("subject", "").strip()
    normalized_subject = normalize_subject(subject)

    conversation_messages = []

    if normalized_subject:
        candidate_messages = (
            Message.objects.select_related("sender")
            .filter(subject__isnull=False)
            .exclude(subject="")
            .order_by("sent_at", "id")
        )

        conversation_messages = [
            candidate
            for candidate in candidate_messages
            if normalize_subject(candidate.subject) == normalized_subject
        ]

    context = {
        "requested_subject": subject,
        "normalized_subject": normalized_subject,
        "conversation_messages": conversation_messages,
    }
    return render(request, "investigation/conversation_detail.html", context)


def dashboard(request):
    total_messages = Message.objects.count()
    total_senders = Employee.objects.count()

    messages_with_date_qs = Message.objects.exclude(sent_at__isnull=True)
    messages_with_date_count = messages_with_date_qs.count()
    messages_without_date_count = total_messages - messages_with_date_count

    messages_with_subject_count = Message.objects.exclude(subject__isnull=True).exclude(subject="").count()
    messages_without_subject_count = total_messages - messages_with_subject_count

    messages_with_sender_count = Message.objects.exclude(sender__isnull=True).count()
    messages_without_sender_count = total_messages - messages_with_sender_count

    messages_with_in_reply_to_count = Message.objects.exclude(in_reply_to_header__isnull=True).exclude(in_reply_to_header="").count()
    messages_without_in_reply_to_count = total_messages - messages_with_in_reply_to_count

    messages_by_month = (
        messages_with_date_qs
        .annotate(month=TruncMonth("sent_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    recent_messages_by_month = list(messages_by_month)[-6:]
    recent_messages_by_month.reverse()

    top_senders = (
        Employee.objects
        .annotate(message_count=Count("sent_messages"))
        .filter(message_count__gt=0)
        .order_by("-message_count", "email")[:10]
    )

    messages_for_conversations = Message.objects.exclude(subject__isnull=True).exclude(subject="")
    normalized_subjects = []

    for message in messages_for_conversations:
        normalized = normalize_subject(message.subject)
        if normalized:
            normalized_subjects.append(normalized)

    counts = Counter(normalized_subjects)
    conversation_count = sum(1 for count in counts.values() if count > 1)

    context = {
        "total_messages": total_messages,
        "total_senders": total_senders,
        "messages_with_date_count": messages_with_date_count,
        "messages_without_date_count": messages_without_date_count,
        "messages_with_subject_count": messages_with_subject_count,
        "messages_without_subject_count": messages_without_subject_count,
        "messages_with_sender_count": messages_with_sender_count,
        "messages_without_sender_count": messages_without_sender_count,
        "messages_with_in_reply_to_count": messages_with_in_reply_to_count,
        "messages_without_in_reply_to_count": messages_without_in_reply_to_count,
        "messages_by_month": messages_by_month,
        "recent_messages_by_month": recent_messages_by_month,
        "top_senders": top_senders,
        "conversation_count": conversation_count,
    }
    return render(request, "investigation/dashboard.html", context)