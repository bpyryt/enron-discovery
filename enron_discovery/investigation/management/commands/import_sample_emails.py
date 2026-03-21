import os
import random
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from investigation.models import Employee, Message, MessageRecipient


DEFAULT_DATASET_ROOT = r"C:\Users\gaspa\OneDrive\Bureau\projet_enron_discovery\enron_mail_20150507\maildir"


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


def read_path_list(path_list_file):
    encodings_to_try = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"]

    for encoding in encodings_to_try:
        try:
            with open(path_list_file, "r", encoding=encoding) as f:
                lines = [line.strip().lstrip("\ufeff") for line in f if line.strip()]
            return lines
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Impossible de décoder le fichier : {path_list_file}")


class Command(BaseCommand):
    help = "Importe un échantillon de fichiers email en base"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Nombre de fichiers à importer aléatoirement",
        )

        parser.add_argument(
            "--path-list",
            type=str,
            help="Chemin vers un fichier texte contenant une liste de chemins de mails à importer",
        )

        parser.add_argument(
            "--dataset-root",
            type=str,
            default=DEFAULT_DATASET_ROOT,
            help="Chemin vers la racine du dataset maildir pour l'import aléatoire",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        limit = options["limit"]
        path_list_file = options.get("path_list")
        dataset_root = options["dataset_root"]

        if path_list_file:
            if not os.path.exists(path_list_file):
                self.stdout.write(
                    self.style.ERROR(f"Fichier de chemins introuvable : {path_list_file}")
                )
                return

            selected_files = read_path_list(path_list_file)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Liste de chemins chargée : {len(selected_files)} fichiers"
                )
            )
        else:
            if not os.path.exists(dataset_root) or not os.path.isdir(dataset_root):
                self.stdout.write(
                    self.style.ERROR(f"Dossier dataset introuvable : {dataset_root}")
                )
                return

            all_files = []

            for root, _, files in os.walk(dataset_root):
                for filename in files:
                    all_files.append(os.path.join(root, filename))

            random.shuffle(all_files)
            selected_files = all_files[:limit]

            self.stdout.write(
                self.style.SUCCESS(
                    f"Dossier scanné : {dataset_root}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Échantillon aléatoire sélectionné : {len(selected_files)} fichiers"
                )
            )

        if not selected_files:
            self.stdout.write(self.style.WARNING("Aucun fichier email trouvé."))
            return

        imported = 0
        skipped_existing = 0
        errors = 0
        linked_threads = 0

        for file_path in selected_files:
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
                    skipped_existing += 1
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
                errors += 1
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
                f"Import terminé. "
                f"Importés: {imported} | "
                f"Déjà présents: {skipped_existing} | "
                f"Erreurs: {errors} | "
                f"Threads liés: {linked_threads}"
            )
        )