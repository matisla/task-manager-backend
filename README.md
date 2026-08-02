# Task Manager Backend

Backend d'une application de gestion de tâches, construit avec **Python** et **FastAPI**, suivant des standards modernes (typage explicite, migrations versionnées, tests automatisés).
Ce projet sert de base d'apprentissage pour de futurs projets sur cette même stack technique.

## Stack technique

- **Langage** : Python 3.14
- **Framework** : FastAPI
- **Serveur ASGI** : Uvicorn
- **Gestion des dépendances** : [uv](https://docs.astral.sh/uv/)
- **Base de données** : SQLite (tests), PostgreSQL (dev / production)
- **ORM / Driver** : SQLModel
- **Migrations** : Alembic
- **Validation** : Pydantic
- **Gestion des paramètres** : Pydantic Settings
- **Authentification** : JWT (access / refresh token), hash de mot de passe Argon2 (`pwdlib`)
- **Linter** : ruff
- **Formatters** : black, isort
- **Tests** : pytest, factory_boy, Faker, httpx

## Fonctionnalités

- Inscription / authentification par JWT (`/auth/register`, `/auth/login`, `/auth/refresh`)
- Récupération de l'utilisateur courant (`/users/me`)
- Gestion des tâches (CRUD) rattachées à l'utilisateur authentifié (`/tasks`), avec support de sous-tâches (relation parent / enfant) et d'un statut de cycle de vie (`backlog`, `paused`, `waiting`, `planned`, `in_progress`, `done`)

## Structure du projet

```
app/
|---- <feature>          # séparation par domaine fonctionnel: auth, tasks, core, ...
      |---- __init__.py
      |---- schemas.py
      |---- models.py
      |---- router.py
      |---- services.py
      |---- ...
|---- config
      |---- __init__.py
      |---- core.py      # classe Settings principale
      |---- logging.py   # schémas et configuration du logging
      |---- database.py  # schémas et configuration de la base de données
      |---- ...
|---- __init__.py
|---- database.py   # générateur de session et d'engine
|---- main.py        # construction de l'app FastAPI
|---- asgi.py         # point d'entrée pour uvicorn
alembic/             # migrations Alembic (env.py, versions/)
tests/
|---- <feature>       # tests pour app/<feature>
|---- ...              # contient conftest.py, factories, etc.

scripts/              # scripts utilitaires
Dockerfile            # image de l'application
docker-compose.yml    # environnement docker de dev (app, PostgreSQL, adminer)
pyproject.toml        # configuration du projet, géré via uv
justfile              # commandes courantes (test, build, migrations, ...)
alembic.ini           # configuration Alembic
env/logging.yaml      # configuration du module logging
.env                  # variables d'environnement locales (non commité)
```

## Prérequis

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Docker et Docker Compose (pour la base PostgreSQL et le déploiement en conteneur)

## Installation

```bash
# installer les dépendances du projet
uv sync

# créer un fichier .env à la racine avec les variables nécessaires
# (voir app/config/core.py, app/config/database.py, app/auth/settings.py
# pour la liste des variables et leurs préfixes: DATABASE_, AUTH_, LOG_)
```

## Lancer le projet en développement

```bash
# démarrer l'application et la base PostgreSQL (via docker compose)
just start
# équivalent à: docker compose up --build -d

# suivre les logs de l'application
just log
```

L'API est alors disponible sur `http://localhost:8000`, avec la documentation interactive sur `/docs` (Swagger) et `/redoc` en environnement de développement. Un client [Adminer](https://www.adminer.org/) est également exposé sur `http://localhost:8080` pour explorer la base PostgreSQL.

## Base de données et migrations

Les migrations de schéma sont gérées avec Alembic. `alembic/env.py` construit dynamiquement l'URL de connexion à partir des settings de l'application (`DatabaseSettings`), il n'y a donc rien à configurer séparément dans `alembic.ini`.

```bash
# créer une nouvelle révision après modification d'un models.py
just makemigrations "message décrivant le changement"
# équivalent à: uv run alembic revision --autogenerate -m "message"

# appliquer les migrations
uv run alembic upgrade head
```

## Tests

```bash
# lancer la suite de tests (utilise tests/database.db en SQLite)
just test
# équivalent à: uv run pytest
```

## Commandes utiles (justfile)

| Commande | Description |
| --- | --- |
| `just start` | démarre l'app et ses dépendances via docker compose |
| `just log` | affiche les logs du conteneur de l'application |
| `just build` | régénère `requirements.txt` et reconstruit l'image `app` |
| `just requirements` | régénère `requirements.txt` à partir de `pyproject.toml` |
| `just test [args]` | lance la suite de tests pytest |
| `just makemigrations "msg"` | crée une révision Alembic (autogenerate) |
| `just clean` | supprime les fichiers générés (`__pycache__`, `.pyc`, base de tests, logs) |

## Qualité de code

```bash
# linter
uvx ruff check .

# formatters
uvx black .
uvx isort .
```
