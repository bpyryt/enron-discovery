from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models


class Employee(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.email


class Message(models.Model):
    message_id_header = models.CharField(max_length=500, unique=True, blank=True, null=True)
    subject = models.CharField(max_length=500, blank=True, null=True)
    body_text = models.TextField(blank=True, null=True)
    body_clean = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    sender = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
    )

    in_reply_to_header = models.CharField(max_length=500, blank=True, null=True)

    parent_message = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )

    raw_path = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            GinIndex(
                SearchVector("subject", weight="A", config="english")
                + SearchVector("body_clean", weight="B", config="english")
                + SearchVector("body_text", weight="C", config="english"),
                name="message_fts_gin_idx",
            ),
        ]

    def __str__(self):
        return self.subject or f"Message {self.id}"


class MessageRecipient(models.Model):
    RECIPIENT_TYPE_CHOICES = [
        ("to", "To"),
        ("cc", "Cc"),
        ("bcc", "Bcc"),
    ]

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="recipients",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )

    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPE_CHOICES)

    def __str__(self):
        return f"{self.message.id} -> {self.employee.email} ({self.recipient_type})"