import os
import random
from email import policy
from email.parser import BytesParser

DATASET_ROOT = r"C:\Users\gaspa\OneDrive\Bureau\projet_enron_discovery\enron_mail_20150507\maildir"
SCAN_LIMIT = 30000
MAX_EXPORT = 5000


def to_windows_path(path: str) -> str:
    if path.startswith("\\\\?\\"):
        return path
    return "\\\\?\\" + path


def parse_headers(file_path: str):
    try:
        win_path = to_windows_path(file_path)
        with open(win_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        return {
            "message_id": msg.get("Message-ID"),
            "in_reply_to": msg.get("In-Reply-To"),
            "references": msg.get("References"),
            "subject": msg.get("Subject"),
            "from": msg.get("From"),
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    all_files = []

    print("Recensement des fichiers...")
    for root, _, files in os.walk(DATASET_ROOT):
        for filename in files:
            all_files.append(os.path.join(root, filename))

    print(f"Total fichiers trouvés : {len(all_files)}")

    random.shuffle(all_files)
    selected_files = all_files[:SCAN_LIMIT]

    print(f"Scan d'un échantillon aléatoire de {len(selected_files)} fichiers...")

    reply_subject_hits = []
    discussion_thread_hits = []
    combined_candidates = []
    errors = []

    seen_paths = set()

    for i, file_path in enumerate(selected_files, start=1):
        result = parse_headers(file_path)

        if "error" in result:
            errors.append((file_path, result["error"]))
            continue

        subject = (result.get("subject") or "").strip()
        lowered_path = file_path.lower()

        is_reply_subject = subject.lower().startswith("re:")
        is_discussion_thread = "discussion_threads" in lowered_path

        if is_reply_subject:
            reply_subject_hits.append((file_path, result))

        if is_discussion_thread:
            discussion_thread_hits.append((file_path, result))

        if (is_reply_subject or is_discussion_thread) and file_path not in seen_paths:
            combined_candidates.append((file_path, result))
            seen_paths.add(file_path)

        if i % 1000 == 0:
            print(
                f"{i}/{len(selected_files)} | "
                f"Re:: {len(reply_subject_hits)} | "
                f"discussion_threads: {len(discussion_thread_hits)} | "
                f"candidats uniques: {len(combined_candidates)} | "
                f"Erreurs: {len(errors)}"
            )

    print("\n=== RÉSULTATS ===")
    print(f"Fichiers scannés : {len(selected_files)}")
    print(f"Sujets commençant par Re: : {len(reply_subject_hits)}")
    print(f"Fichiers dans discussion_threads : {len(discussion_thread_hits)}")
    print(f"Candidats uniques à importer : {len(combined_candidates)}")
    print(f"Erreurs de lecture : {len(errors)}")

    export_count = min(MAX_EXPORT, len(combined_candidates))

    with open("thread_candidate_paths.txt", "w", encoding="utf-8") as out:
        for file_path, _ in combined_candidates[:export_count]:
            out.write(file_path + "\n")

    with open("thread_candidates_preview.txt", "w", encoding="utf-8") as out:
        out.write("=== APERÇU DES CANDIDATS ===\n\n")
        for file_path, result in combined_candidates[:200]:
            out.write(f"PATH: {file_path}\n")
            out.write(f"FROM: {result.get('from')}\n")
            out.write(f"SUBJECT: {result.get('subject')}\n")
            out.write(f"MESSAGE-ID: {result.get('message_id')}\n")
            out.write(f"IN-REPLY-TO: {result.get('in_reply_to')}\n")
            out.write(f"REFERENCES: {result.get('references')}\n")
            out.write("\n")

    print(f"\nFichiers générés :")
    print(f"- thread_candidate_paths.txt ({export_count} chemins)")
    print(f"- thread_candidates_preview.txt")


if __name__ == "__main__":
    main()