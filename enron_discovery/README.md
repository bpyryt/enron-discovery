# Enron Discovery

Application web d’exploration d’emails construite avec **Django**, **PostgreSQL** et **Docker** à partir du dataset **Enron Email Dataset**.

Le projet permet de :

- importer un échantillon d’emails Enron en base PostgreSQL,
- consulter les messages dans une interface Django,
- afficher le détail d’un message,
- effectuer une recherche simple et une recherche **full-text PostgreSQL**,
- filtrer les messages par expéditeur et par dates,
- afficher un dashboard global avec des statistiques sur les emails,
- préparer l’exploration des threads de discussion.

---

## Stack technique

- **Python**
- **Django**
- **PostgreSQL**
- **Docker / Docker Compose**
- **HTML / templates Django**

---

## Fonctionnalités implémentées

### 1. Import d’emails Enron
Un script de management Django permet d’importer un échantillon du dataset Enron en base.

Les informations extraites incluent notamment :

- l’identifiant du message,
- le sujet,
- le corps brut,
- le corps nettoyé,
- la date d’envoi,
- l’expéditeur,
- les destinataires,
- les en-têtes `Message-ID` et `In-Reply-To`,
- le chemin brut du fichier source.

### 2. Liste des messages
Page disponible sur :

```text
/messages/