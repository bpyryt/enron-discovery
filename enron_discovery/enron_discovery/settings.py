from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Charge le .env local si présent (utile en dev)
load_dotenv(PROJECT_ROOT / '.env')

# =========================
# Sécurité / environnement
# =========================

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-secret-key')

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Render injecte automatiquement ce hostname en prod
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Si tu veux forcer d'autres hosts via variable d'env
EXTRA_ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS')
if EXTRA_ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend([host.strip() for host in EXTRA_ALLOWED_HOSTS.split(',') if host.strip()])

# =========================
# Applications
# =========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'investigation',
]

# =========================
# Middleware
# =========================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # important pour Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'enron_discovery.urls'

# =========================
# Templates
# =========================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'enron_discovery.wsgi.application'
ASGI_APPLICATION = 'enron_discovery.asgi.application'

# =========================
# Base de données
# =========================

# En prod (Render), DATABASE_URL sera fournie automatiquement si tu la configures
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Config locale actuelle (compatible avec ton Docker/PostgreSQL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'enron_discovery'),
            'USER': os.getenv('DB_USER', 'enron_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'enron_pass'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# =========================
# Validation mot de passe
# =========================

AUTH_PASSWORD_VALIDATORS = []

# =========================
# Internationalisation
# =========================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# =========================
# Fichiers statiques
# =========================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django 5+ : config recommandée
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# =========================
# Proxy HTTPS (Render)
# =========================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =========================
# Clé primaire par défaut
# =========================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'