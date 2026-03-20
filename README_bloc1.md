# Bloc 1 — Setup initial

## 1) Créer l'environnement
```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
pip install -r requirements.txt
cp .env.example .env
```

## 2) Lancer PostgreSQL
```bash
docker compose up -d
```

## 3) Lancer Django
```bash
cd enron_discovery
python manage.py migrate
python manage.py runserver
```

## 4) Vérifier
- La DB PostgreSQL écoute sur `localhost:5432`
- Django répond sur `http://127.0.0.1:8000/`

## 5) Ce qu'il reste à faire ensuite
- ajouter les modèles `employees`, `messages`, `message_recipients`
- créer le parser `.eml`
- brancher la recherche PostgreSQL
