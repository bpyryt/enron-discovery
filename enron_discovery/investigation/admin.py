from django.contrib import admin
from .models import Employee, Message, MessageRecipient


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name")
    search_fields = ("email", "name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "sender", "sent_at")
    search_fields = ("subject", "body_text", "body_clean", "message_id_header")
    list_filter = ("sent_at",)


@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "employee", "recipient_type")
    list_filter = ("recipient_type",)
    search_fields = ("employee__email", "message__subject")