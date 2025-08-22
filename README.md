# Tribeo – Backend (Django + DRF)
![build](https://img.shields.io/badge/build-passing-brightgreen)
![tests](https://img.shields.io/badge/tests-pytest-blue)
![python](https://img.shields.io/badge/python-3.11-%233776AB)
![django](https://img.shields.io/badge/django-4.x-092E20)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

API REST de **Tribeo** construite avec **Django + DRF**.  
Auth **JWT**, gestion des **groupes** & **sessions sportives**, **quotas** par rôle et **abonnements Stripe**. Déployable sur **Render**.

---

## Sommaire
- [Fonctionnalités](#fonctionnalités)
- [Stack & Architecture](#stack--architecture)
- [Installation rapide](#installation-rapide)
- [Configuration (.env)](#configuration-env)
- [Commandes utiles](#commandes-utiles)
- [Structure du projet](#structure-du-projet)
- [Documentation API](#documentation-api)
- [Flux d’authentification](#flux-dauthentification)
- [Stripe (abonnements)](#stripe-abonnements)
- [Sécurité](#sécurité)
- [Tests & Qualité](#tests--qualité)
- [Déploiement (Render)](#déploiement-render)
- [Dépannage](#dépannage)
- [Licence](#licence)

---

## Fonctionnalités
- 🔐 **JWT** (login par **email ou username**), refresh + blacklist.
- 👤 **Profil** utilisateur (GET / PATCH / **DELETE = désactivation**).
- 👥 **Groupes** (création, adhésion, invitations, gestion).
- 🏋️ **Sessions sportives** (création, participation, présence).
- 📊 **Quotas & rôles** : `member` (gratuit), `premium`, `coach`, `admin/staff`.
- 🚦 **Rate limiting / anti brute-force** sur endpoints sensibles (ex. login → `429`).
- 🌍 **CORS/CSRF** configurables pour un frontend Vite/React.
- 💳 **Stripe** : abonnements **Premium** & **Coach** + **webhooks**.
- 🧰 **OpenAPI/Swagger** intégré (`/api/docs/`).
- 🐘 **PostgreSQL** (SSL requis en prod).

---

## Stack & Architecture
- **Django 4.x**, **Django REST Framework**
- **djangorestframework-simplejwt** (ou équivalent)
- **PostgreSQL**
- **Stripe** (Checkout + Webhooks)
- **Gunicorn** pour la prod
- Déploiement cible : **Render**

**Principes**
- Séparation par **apps** (accounts, groups, sessions, quotas, billing…)
- Sérialiseurs et **permissions** explicites
- Services/utilitaires isolés (facturation, quotas…)

---

## Installation rapide

> Prérequis : **Python 3.11**, **PostgreSQL**, **virtualenv**

```bash
# 1) Cloner
git clone https://github.com/username/tribeo-backend.git
cd tribeo-backend

# 2) Environnement virtuel
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

# 3) Dépendances
pip install -r requirements.txt

# 4) Variables d'environnement
cp .env.sample .env

# 5) Base de données & superuser
python manage.py migrate
python manage.py createsuperuser

# 6) Lancer en local
python manage.py runserver