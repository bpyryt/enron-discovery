import os
import random
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, getaddresses

from django.core.management.base import BaseCommand
from django.db import transaction

from investigation.models import Employee, Message, MessageRecipient


def extract_text_from_message(msg):
    """Extrait le corps texte d'un email."""
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    parts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        parts.append(payload.decode(errors="replace"))
        return "\n".join(parts).strip()
    else:
        try:
            return msg.get_content().strip()
        except Exception:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace").strip()
    return ""


def clean_body(text):
    """Nettoyage très simple pour MVP."""
    if not text:
        return ""

    markers = [
        "-----Original Message-----",
        "From:",
        "Sent:",
        "To:",
        "Subject:",
    ]

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        if any(marker in line for marker in markers):
            break
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def get_or_create_employee(email_value):
    if not email_value:
        return None

    email_value = email_value.strip().lower()
    if not email_value:
        return None

    employee, _ = Employee.objects.get_or_create(email=email_value)
    return employee


def to_windows_path(path):
    path_str = str(path)

    if os.name == "nt":
        path_str = path_str.replace("/", "\\")
        if not path_str.startswith("\\\\?\\"):
            path_str = "\\\\?\\" + path_str

    return path_str


class Command(BaseCommand):
    help = "Importe un petit échantillon de fichiers email en base"

    def add_arguments(self, parser):
        parser.add_argument("folder", type=str, help="Chemin vers le dossier contenant les emails")
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Nombre max de fichiers à importer",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        folder = Path(options["folder"])
        limit = options["limit"]

        if not folder.exists() or not folder.is_dir():
            self.stdout.write(self.style.ERROR(f"Dossier introuvable : {folder}"))
            return

        all_files = []
        for root, dirs, files in os.walk(folder):
            for filename in files:
                all_files.append(os.path.join(root, filename))

        random.shuffle(all_files)
        eml_files = all_files[:limit]

        self.stdout.write(f"Dossier scanné : {folder}")
        self.stdout.write(f"Fichiers trouvés : {len(eml_files)}")

        if not eml_files:
            self.stdout.write(self.style.WARNING("Aucun fichier email trouvé."))
            return

        imported = 0
        skipped = 0
        linked_threads = 0

        for file_path in eml_files:
            try:
                safe_path = to_windows_path(file_path)

                with open(safe_path, "rb") as f:
                    msg = BytesParser(policy=policy.default).parse(f)

                from_header = msg.get("From", "")
                to_header = msg.get("To", "")
                cc_header = msg.get("Cc", "")
                bcc_header = msg.get("Bcc", "")
                subject = msg.get("Subject", "")
                message_id_header = msg.get("Message-ID", "")
                in_reply_to_header = msg.get("In-Reply-To", "")
                date_header = msg.get("Date", "")

                body_text = extract_text_from_message(msg)
                body_clean = clean_body(body_text)

                sent_at = None
                if date_header:
                    try:
                        sent_at = parsedate_to_datetime(date_header)
                    except Exception:
                        sent_at = None

                sender_addresses = getaddresses([from_header])
                sender_email = sender_addresses[0][1].lower() if sender_addresses else None
                sender = get_or_create_employee(sender_email)

                message, created = Message.objects.get_or_create(
                    message_id_header=message_id_header or None,
                    defaults={
                        "subject": subject,
                        "body_text": body_text,
                        "body_clean": body_clean,
                        "sent_at": sent_at,
                        "sender": sender,
                        "in_reply_to_header": in_reply_to_header or None,
                        "raw_path": file_path,
                    },
                )

                if not created:
                    skipped += 1
                    continue

                recipients_map = [
                    ("to", to_header),
                    ("cc", cc_header),
                    ("bcc", bcc_header),
                ]

                for recipient_type, header_value in recipients_map:
                    addresses = getaddresses([header_value])
                    for _, email_value in addresses:
                        email_value = (email_value or "").strip().lower()
                        if not email_value:
                            continue

                        employee = get_or_create_employee(email_value)
                        if employee:
                            MessageRecipient.objects.get_or_create(
                                message=message,
                                employee=employee,
                                recipient_type=recipient_type,
                            )

                imported += 1

            except Exception as e:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"Erreur sur {file_path}: {e}")
                )

        messages_with_reply_header = Message.objects.exclude(
            in_reply_to_header__isnull=True
        ).exclude(
            in_reply_to_header=""
        )

        for message in messages_with_reply_header:
            parent = Message.objects.filter(
                message_id_header=message.in_reply_to_header
            ).first()

            if parent and message.parent_message_id != parent.id:
                message.parent_message = parent
                message.save(update_fields=["parent_message"])
                linked_threads += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé. Importés: {imported} | Ignorés/erreurs: {skipped} | Threads liés: {linked_threads}"
            )
        )