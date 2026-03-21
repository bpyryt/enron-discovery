from django.http import HttpResponse


def index(_request):
    return HttpResponse('Investigation app ready')


from django.shortcuts import render
from .models import Message


def message_list(request):
    messages = Message.objects.all().order_by("-id")[:100]
    return render(request, "investigation/message_list.html", {"messages": messages})