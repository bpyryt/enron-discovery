## Enron Discovery

# Présentation du projet:

Enron Discovery est une application web développée avec Django permettant d’explorer un sous-ensemble du corpus d’emails bruts Enron et de le transformer en système d'exploration analytique.

# L’objectif du projet est de :

Lire des fichiers emails au format .eml (Ingestion),
Extraire les données utiles des headers email (expéditeur, destinataires, date, sujet, etc.)(Parsing),
Nettoyer le contenu textuel,
Stocker les données dans une base PostgreSQL,
Proposer une recherche textuelle avancée,
Afficher un dashboard statistique,
Permettre l’exploration de conversations entre emails.

# Le projet repose sur la stack suivante :

Python
Django
PostgreSQL
Docker / Docker Compose
Pandas

Le développement a été réalisé sous Windows, avec Docker Desktop pour la base de données PostgreSQL.

# Objectifs du projet

Ce projet répond à plusieurs objectifs techniques et fonctionnels :

Utiliser Django comme framework backend,
Utiliser PostgreSQL comme base de données relationnelle,
Mettre en place un pipeline d’ingestion et de parsing d’emails,
Exploiter Pandas dans la phase d’ingestion,
Proposer une recherche full-text native PostgreSQL,
Afficher des statistiques globales dans un dashboard,
Explorer les fils de discussion / conversations,
Maintenir un dépôt Git propre et documenté.


# Stack technique:

Backend -> Python / Django
Base de données -> PostgreSQL
Conteneurisation -> Docker / Docker Compose
Analyse / ingestion -> Pandas
Frontend -> Templates Django / HTML 
Environnement de développement -> Windows / VS Code / Docker Desktop / venv (environnement virtuel Python)

Structure générale du projet

# Arborescence principale :

enron_discovery/
    enron_discovery/
        settings.py
        urls.py
    investigation/
        management/
            commands/
                import_sample_emails.py
                import_emails_pandas.py
        migrations/
        templates/
            investigation/
                base.html
                home.html
                dashboard.html
                message_list.html
                message_detail.html
                conversation_list.html
                conversation_detail.html
        models.py
        urls.py
        views.py
    manage.py
    README.md
    docker-compose.yml

# Modélisation des données

La base de données est définie à travers les modèles Django dans investigation/models.py.
Cela signifie que le schéma SQL n’est pas écrit “à la main” dans un fichier .sql, mais qu’il est généré automatiquement par Django via les migrations.

1. Modèle Employee

Le modèle Employee représente une adresse email (expéditeur ou destinataire).
Il permet de centraliser les personnes apparaissant dans les emails.

Champs principaux :

    email
    nom éventuel (si disponible)

2. Modèle Message

Le modèle Message représente un email individuel.

Champs principaux :

    message_id_header : identifiant technique du message (Message-ID)
    subject : objet du mail
    body_text : corps brut du message
    body_clean : corps nettoyé (version simplifiée)
    sent_at : date d’envoi
    sender : expéditeur (lié à Employee)
    in_reply_to_header : valeur brute du header In-Reply-To
    parent_message : relation vers un éventuel message parent
    raw_path : chemin du fichier source dans le dataset


3. Modèle MessageRecipient

Le modèle MessageRecipient sert de table de liaison entre un message et ses destinataires.
Il permet de distinguer les différents types de destinataires :

    to
    cc
    bcc

Champs principaux :

    message
    employee
    recipient_type

# Fonctionnalités implémentées

1. Import d’emails Enron

Une première commande Django permet d’importer un échantillon du dataset Enron en base.

Fichier concerné :

investigation/management/commands/import_sample_emails.py

Cette commande :

    -Scanne le dataset ou charge une liste de chemins ciblés,
    -Ouvre les fichiers .eml,
    -Parse les en-têtes email,
    -Extrait les métadonnées,
    -Récupère le corps texte,
    -Nettoie le contenu,
    -Crée les objets Django en base.

Les informations extraites incluent notamment :

    l’identifiant du message,
    le sujet,
    le corps brut,
    le corps nettoyé,
    la date d’envoi,
    l’expéditeur,
    les destinataires,
    les en-têtes Message-ID et In-Reply-To,
    le chemin brut du fichier source.

Exemples de commandes :

python manage.py import_sample_emails --limit 100
python manage.py import_sample_emails --path-list thread_candidate_paths_500.txt

2. Pipeline d’ingestion avec Pandas

Une seconde commande d’import a été ajoutée pour répondre explicitement à l’exigence d’un pipeline Pandas.

Fichier concerné :

investigation/management/commands/import_emails_pandas.py

Cette commande suit une logique plus structurée :

    scan des fichiers .eml,
    parsing des emails,
    extraction des métadonnées,
    structuration des données dans un DataFrame Pandas,
    normalisation / nettoyage simple des champs,
    déduplication simple sur Message-ID,
    insertion des données dans PostgreSQL via l’ORM Django,
    tentative de reconstruction des relations In-Reply-To.

Concrètement, cela permet de montrer que Pandas n’est pas seulement mentionné dans le projet, mais réellement utilisé dans la phase d’ingestion.

Exemples de commandes :

python manage.py import_emails_pandas --limit 100
python manage.py import_emails_pandas --path-list thread_candidate_paths_500.txt

3. Nettoyage du corps des emails

Le projet extrait le contenu texte des emails en privilégiant les parties text/plain.
Un nettoyage simple (MVP) est appliqué afin de :

supprimer certaines signatures ou reprises de message,
couper le texte à partir de marqueurs courants comme :
-----Original Message-----
From:
Sent:
To:
Subject:

L’objectif est d’obtenir une version plus exploitable du contenu dans le champ :

    body_clean

Ce nettoyage reste volontairement simple, mais il est déjà utile pour la recherche et l’affichage.

4. Gestion des relations In-Reply-To

Le modèle de données prévoit une reconstruction des fils de discussion via les en-têtes email standards :

    Message-ID
    In-Reply-To

Le fonctionnement théorique est le suivant :

un message possède un Message-ID,
un message réponse peut contenir un In-Reply-To,
si la valeur de In-Reply-To correspond au Message-ID d’un autre message, alors on peut relier les deux.

Dans ce projet :

la valeur brute de In-Reply-To est bien stockée,
une tentative de liaison vers parent_message est effectuée après import.

Important : cette fonctionnalité est bien implémentée techniquement, mais son efficacité dépend fortement de la qualité des données du corpus (voir section dédiée plus bas).

5. Liste des messages

Une vue permet d’afficher la liste des messages importés.

Route :

/messages/

Cette page affiche notamment :

le sujet,
l’expéditeur,
la date,
un extrait du contenu.

Elle constitue la page principale d’exploration des emails.

6. Recherche simple et filtres

La liste des messages propose :

une recherche textuelle simple,
un filtre par expéditeur,
des filtres de date,
un tri chronologique.

Ces fonctionnalités permettent de naviguer plus facilement dans le corpus.

7. Recherche Full-Text Search PostgreSQL

La page /messages/ utilise également la recherche full-text native de PostgreSQL.

Cette fonctionnalité repose sur :

SearchVector
SearchQuery
SearchRank
Pondération des champs

Le moteur de recherche donne plus ou moins d’importance selon le champ :

subject → poids A
body_clean → poids B
body_text → poids C

En pratique :

le sujet est considéré comme le plus important,
le corps nettoyé est également fortement valorisé,
le corps brut reste pris en compte, mais avec une pondération plus faible.
Indexation

Un index GIN a été ajouté pour accélérer les recherches full-text dans PostgreSQL.

Cela améliore les performances lorsque le volume de données augmente.

8. Détail d’un message

Une vue permet d’afficher le détail complet d’un email.

Route :

/messages/<id>/

Cette page affiche :

le sujet,
l’identifiant interne,
l’expéditeur,
la date,
le Message-ID,
le In-Reply-To,
le chemin brut du fichier (raw_path),
les destinataires,
le corps complet du message,
les réponses liées via headers (quand disponibles),
la conversation probable associée.

9. Dashboard global

Une vue dédiée fournit un tableau de bord statistique global.

Route :

/dashboard/

Cette page affiche notamment :

le nombre total de messages,
le nombre total d’expéditeurs,
le volume de messages par mois,
le top des expéditeurs.

L’objectif est d’avoir une vision synthétique du corpus importé.

10. Page d’accueil et interface générale

Une page d’accueil a été ajoutée pour structurer la navigation.

Route :

/

L’interface comprend :

une page d’accueil,
un menu de navigation,
un template de base partagé,
une interface plus homogène pour :
l’accueil,
le dashboard,
la liste des messages,
le détail d’un message,
les conversations.

11. Explorateur de conversations probables

Un explorateur de conversations a été ajouté pour répondre au besoin d’analyse chronologique des échanges.

Routes :

/conversations/
/conversation/?subject=...

Cette fonctionnalité ne repose pas uniquement sur les en-têtes RFC, mais sur une heuristique de regroupement par sujet :

le sujet est normalisé,
les préfixes répétés comme Re:, FW:, Fwd: sont supprimés,
les messages partageant le même sujet normalisé sont regroupés,
l’ensemble est trié par ordre chronologique.

Cette approche permet d’obtenir une conversation probable, même lorsque les en-têtes techniques sont absents ou incomplets.

# Analyse conversationnelle : limite du corpus et solution retenue

1. Ce qui était prévu initialement

Le projet prévoyait une reconstruction des fils de discussion à partir des en-têtes standards :

    In-Reply-To
    References

Le modèle de données a été conçu dans ce sens, avec notamment :

    in_reply_to_header
    parent_message

2. Ce qui a été observé dans le corpus

Après analyse du corpus importé, plusieurs constats ont été faits :

de nombreux messages ont un sujet commençant par Re:,
de nombreux fichiers sont situés dans des dossiers liés à des échanges,
mais les en-têtes In-Reply-To sont très peu renseignés,
les en-têtes References sont absents ou non exploitables sur l’échantillon étudié.

Autrement dit :

le threading RFC classique est prévu techniquement,
mais les données réelles du corpus ne permettent pas de l’exploiter efficacement.

3. Solution de repli mise en place

Pour répondre malgré tout au besoin d’exploration conversationnelle, une stratégie de repli a été implémentée :

normalisation du sujet,
suppression des préfixes :
Re:
FW:
Fwd:
regroupement des messages partageant le même sujet normalisé,
tri chronologique.

Cette stratégie est volontairement présentée comme une conversation probable.

Elle ne prétend pas reconstruire un thread RFC parfait, mais elle fournit une réponse cohérente.

# Routes principales de l’application

/ → page d’accueil
/dashboard/ → dashboard global
/messages/ → liste des messages + recherche + filtres
/messages/<id>/ → détail d’un message
/conversations/ → liste des conversations probables
/conversation/?subject=... → détail chronologique d’une conversation probable
/admin/ → interface d’administration Django

# Spécificité Windows : gestion des fichiers finissant par un point

Le dataset Enron contient des fichiers dont le nom se termine par un point, par exemple :

1.
10.
100.

Sous Windows, ce type de nom pose problème lors de l’ouverture ou de la normalisation des chemins.

Correctif appliqué

Une logique de chemin Windows long a été utilisée :

ajout du préfixe \\?\
remplacement des / par \

Cette approche permet d’ouvrir correctement les fichiers concernés sans perdre leur nom exact.

Point important :

Il faut éviter d’utiliser os.path.abspath() dans ce contexte, car cela peut supprimer le point final du nom de fichier sous Windows.

C’est un point important pour ce dataset spécifique.

# Installation et lancement

1. Cloner le dépôt

Commande :

git clone https://github.com/bpyryt/enron-discovery.git

Puis se placer dans le dossier contenant manage.py :

cd enron-discovery/enron_discovery

2. Créer et activer l’environnement virtuel (Windows)

Commandes :

python -m venv .venv
.\.venv\Scripts\activate

3. Installer les dépendances

Commande :

pip install -r requirements.txt

4. Configurer les variables d’environnement

Créer le fichier .env à partir de .env.example.

Exemple PowerShell :

Copy-Item .env.example .env

5. Lancer PostgreSQL via Docker

Commande :

docker compose up -d

6. Appliquer les migrations

Commande :

python manage.py migrate

7. Créer un superutilisateur

Commande :

python manage.py createsuperuser

8. Lancer le serveur Django

Commande :

python manage.py runserver

# Commandes utiles: 
Vérification Django
python manage.py check
python manage.py showmigrations
Import simple
python manage.py import_sample_emails --limit 50
Import ciblé (simple)
python manage.py import_sample_emails --path-list thread_candidate_paths_500.txt
Import via Pandas
python manage.py import_emails_pandas --limit 50
Import ciblé via Pandas
python manage.py import_emails_pandas --path-list thread_candidate_paths_500.txt
Lancer l’application
python manage.py runserver
État actuel du projet
Fonctionnalités actuellement opérationnelles
page d’accueil
dashboard global
liste des messages
détail d’un message
recherche simple + filtres
recherche full-text PostgreSQL
interface admin
import simple
import via pipeline Pandas
explorateur de conversations probables
Fonctionnalités partiellement utiles selon les données
parent_message
réponses liées via In-Reply-To

Ces éléments sont bien implémentés, mais restent peu alimentés sur le corpus testé à cause du manque d’en-têtes RFC exploitables.

Limites actuelles
La reconstruction stricte des threads via In-Reply-To / References est limitée par la qualité des métadonnées du corpus.
Le pipeline Pandas est utilisé côté ingestion, mais pas encore dans l’interface web (ce qui est acceptable et cohérent avec le sujet).
La logique de nettoyage du corps des emails reste volontairement simple (MVP) et pourrait être enrichie.
Pistes d’amélioration
renforcer le pipeline Pandas pour mieux gérer les emails sans Message-ID,
améliorer le nettoyage du corps des messages (signatures, transferts, citations),
ajouter des exports CSV statistiques via Pandas,
affiner la reconstruction conversationnelle avec des heuristiques supplémentaires,
améliorer encore l’interface utilisateur.