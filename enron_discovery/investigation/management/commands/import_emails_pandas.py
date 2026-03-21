import os
import random
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

import pandas as pd
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
                    content = part.get_content()
                    if content:
                        parts.append(content)
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        parts.append(payload.decode(charset, errors="replace"))
        return "\n".join(parts).strip()
    else:
        try:
            return msg.get_content().strip()
        except Exception:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace").strip()
    return ""


def clean_body(text):
    """Nettoyage simple du corps du mail."""
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

    cleaned_text = "\n".join(cleaned_lines).strip()

    while "\n\n\n" in cleaned_text:
        cleaned_text = cleaned_text.replace("\n\n\n", "\n\n")

    return cleaned_text


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


def parse_email_file(file_path):
    """Parse un fichier .eml et renvoie un dict prêt pour pandas."""
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
        sender_email = sender_addresses[0][1].lower().strip() if sender_addresses else ""

        to_emails = [
            email.strip().lower()
            for _, email in getaddresses([to_header])
            if email and email.strip()
        ]
        cc_emails = [
            email.strip().lower()
            for _, email in getaddresses([cc_header])
            if email and email.strip()
        ]
        bcc_emails = [
            email.strip().lower()
            for _, email in getaddresses([bcc_header])
            if email and email.strip()
        ]

        return {
            "raw_path": file_path,
            "subject": (subject or "").strip(),
            "message_id_header": (message_id_header or "").strip(),
            "in_reply_to_header": (in_reply_to_header or "").strip(),
            "sent_at": sent_at,
            "sender_email": sender_email,
            "to_emails": to_emails,
            "cc_emails": cc_emails,
            "bcc_emails": bcc_emails,
            "body_text": body_text,
            "body_clean": body_clean,
            "error": "",
        }

    except Exception as e:
        return {
            "raw_path": file_path,
            "subject": "",
            "message_id_header": "",
            "in_reply_to_header": "",
            "sent_at": None,
            "sender_email": "",
            "to_emails": [],
            "cc_emails": [],
            "bcc_emails": [],
            "body_text": "",
            "body_clean": "",
            "error": str(e),
        }


class Command(BaseCommand):
    help = "Importe des emails en base via un pipeline pandas"

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

        self.stdout.write("Parsing des emails vers un DataFrame pandas...")

        records = []
        for index, file_path in enumerate(selected_files, start=1):
            if index % 250 == 0:
                self.stdout.write(f"{index} fichiers analysés...")
            records.append(parse_email_file(file_path))

        df = pd.DataFrame(records)

        if df.empty:
            self.stdout.write(self.style.WARNING("Aucune donnée exploitable extraite."))
            return

        total_rows = len(df)
        errors_df = df[df["error"] != ""].copy()
        valid_df = df[df["error"] == ""].copy()

        self.stdout.write(
            self.style.SUCCESS(
                f"DataFrame construit : {total_rows} lignes | "
                f"Valides : {len(valid_df)} | "
                f"Erreurs : {len(errors_df)}"
            )
        )

        if valid_df.empty:
            self.stdout.write(self.style.WARNING("Tous les fichiers sont en erreur."))
            return

        # Normalisation / nettoyage pandas
        valid_df["subject"] = valid_df["subject"].fillna("").astype(str).str.strip()
        valid_df["message_id_header"] = valid_df["message_id_header"].fillna("").astype(str).str.strip()
        valid_df["in_reply_to_header"] = valid_df["in_reply_to_header"].fillna("").astype(str).str.strip()
        valid_df["sender_email"] = valid_df["sender_email"].fillna("").astype(str).str.strip().str.lower()
        valid_df["body_text"] = valid_df["body_text"].fillna("").astype(str)
        valid_df["body_clean"] = valid_df["body_clean"].fillna("").astype(str)
        valid_df["raw_path"] = valid_df["raw_path"].fillna("").astype(str)

        # Déduplication sur Message-ID quand disponible
        with_message_id = valid_df[valid_df["message_id_header"] != ""].copy()
        without_message_id = valid_df[valid_df["message_id_header"] == ""].copy()

        before_dedup = len(with_message_id)
        with_message_id = with_message_id.drop_duplicates(
            subset=["message_id_header"],
            keep="first",
        )
        dedup_removed = before_dedup - len(with_message_id)

        valid_df = pd.concat([with_message_id, without_message_id], ignore_index=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Après déduplication pandas : {len(valid_df)} lignes "
                f"(doublons Message-ID supprimés : {dedup_removed})"
            )
        )

        imported = 0
        skipped_existing = 0
        errors = len(errors_df)
        linked_threads = 0

        for _, row in valid_df.iterrows():
            try:
                sender = get_or_create_employee(row["sender_email"])

                message, created = Message.objects.get_or_create(
                    message_id_header=row["message_id_header"] or None,
                    defaults={
                        "subject": row["subject"],
                        "body_text": row["body_text"],
                        "body_clean": row["body_clean"],
                        "sent_at": row["sent_at"],
                        "sender": sender,
                        "in_reply_to_header": row["in_reply_to_header"] or None,
                        "raw_path": row["raw_path"],
                    },
                )

                if not created:
                    skipped_existing += 1
                    continue

                recipients_map = [
                    ("to", row["to_emails"]),
                    ("cc", row["cc_emails"]),
                    ("bcc", row["bcc_emails"]),
                ]

                for recipient_type, emails in recipients_map:
                    for email_value in emails:
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
                    self.style.WARNING(f"Erreur d'import ORM sur {row['raw_path']}: {e}")
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