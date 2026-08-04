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
- **Logs** : [structlog](https://www.structlog.org/), un objet JSON par ligne sur stdout
- **Linter / Formatter** : ruff
- **Vérification de types** : pyright
- **Tests** : pytest, factory_boy, Faker, httpx

## Fonctionnalités

| Méthode  | Route                                   | Description                                                             |
| -------- | ---------------------------------------- | -------------------------------------------------------------------------- |
| `POST`   | `/api/auth/register`                     | Créer un utilisateur                                                       |
| `POST`   | `/api/auth/login`                        | Authentifier un utilisateur (OAuth2 password flow), émettre les tokens     |
| `POST`   | `/api/auth/refresh`                      | Émettre un nouveau couple access/refresh token                             |
| `GET`    | `/api/users/me`                          | Récupérer l'utilisateur authentifié                                        |
| `GET`    | `/api/tasks`                             | Lister les tâches de l'utilisateur (filtres: statut, tâche parente)        |
| `POST`   | `/api/tasks`                             | Créer une tâche                                                            |
| `GET`    | `/api/tasks/{task_id}`                   | Détail d'une tâche                                                         |
| `DELETE` | `/api/tasks/{task_id}`                   | Supprimer une tâche                                                        |
| `POST`   | `/api/tasks/{task_id}/{target_status}`   | Faire transiter une tâche vers un nouveau statut                           |
| `GET`    | `/api/`                                  | Message d'accueil                                                          |
| `GET`    | `/api/health`                            | Healthcheck versionné (vérifie l'accès à la base de données)               |
| `GET`    | `/health`                                | Healthcheck racine, non versionné, utilisé par le `HEALTHCHECK` Docker     |

Une tâche (`Task`) suit un cycle de vie (`backlog`, `planned`, `in_progress`, `paused`, `waiting`,
`done`, `cancelled`, `archived`) ; les transitions autorisées entre statuts sont validées côté
service (`TaskService.transition`). Les tâches supportent des sous-tâches via une relation
parent / enfant. La suppression suit une règle à trois branches (`TaskService.delete`) :
suppression physique pour `backlog`, archivage implicite pour `done`/`cancelled`, opération
idempotente pour `archived`.

Chaque requête reçoit un `request_id` (repris de l'en-tête `X-Request-ID` ou généré) porté par
tous les logs de la requête et renvoyé dans la réponse, via `RequestContextMiddleware`.

## Structure du projet

```
app/
├── api/
│   └── router.py         # assemble les routers de chaque domaine sous /api
├── auth/
│   ├── deps.py            # dépendance FastAPI: utilisateur courant depuis le JWT
│   ├── models.py          # modèle SQLModel User
│   ├── repository.py      # accès base de données pour User
│   ├── router.py          # /auth (register, login, refresh), /users (me)
│   ├── schemas.py         # schémas Pydantic (UserCreate, UserResponse, Token, ...)
│   ├── security.py        # hash de mot de passe (Argon2), JWT (encode/decode)
│   ├── services.py        # logique métier: création utilisateur, login, refresh
│   └── settings.py        # AuthSettings (SECRET_KEY, ALGORITHM, durées de token)
├── core/
│   ├── config/
│   │   ├── core.py         # classe Settings principale, get_settings()/load_settings()
│   │   ├── cors.py         # CORSSettings
│   │   └── logging.py      # LoggingSettings, configuration structlog (JSON sur stdout)
│   ├── exceptions.py      # AppError et sous-classes, handler -> réponses HTTP JSON
│   ├── middlewares.py     # RequestContextMiddleware (request_id, log d'accès)
│   ├── mixins.py          # IDMixin, TimestampMixin (SQLModel)
│   ├── repository.py      # DefaultRepository[ModelType] générique (CRUD)
│   └── router.py          # endpoints transverses (/, /health)
├── db/
│   ├── deps.py             # dépendance FastAPI: session de base de données
│   ├── session.py          # création de l'engine et de la session factory
│   └── settings.py         # DatabaseSettings, construction de l'URL de connexion
├── tasks/
│   ├── filters.py          # TaskFilter (filtres d'égalité pour le listing)
│   ├── models.py           # modèle SQLModel Task (statuts, sous-tâches)
│   ├── repository.py       # accès base de données pour Task
│   ├── router.py           # /tasks (CRUD + transition de statut)
│   ├── schemas.py          # schémas Pydantic (TaskCreate, TaskRead)
│   └── services.py         # logique métier: transitions de statut, suppression
├── asgi.py                  # point d'entrée uvicorn (app.asgi:app)
└── main.py                   # construction de l'app FastAPI (create_app)

alembic/              # migrations (env.py, versions/)
tests/
├── auth/, core/, tasks/  # tests + factories, en miroir de app/
└── conftest.py          # fixtures partagées (engine, session, client, auth_client)

scripts/               # scripts utilitaires (ex: add_user.sh)
Dockerfile             # image de l'application (stage builder / runtime)
docker-compose.yml            # services partagés (db, adminer)
docker-compose.override.yml   # service api (dev, hot-reload) + db-test, fusionné automatiquement
pyproject.toml         # configuration du projet, gérée via uv
justfile               # commandes courantes (test, lint, format, migrations, ...)
alembic.ini            # configuration Alembic
env/logging.yaml       # config uvicorn (non branchée sur le logging applicatif, cf. plus bas)
```

> Le modèle `Routine` (récurrence de tâches) existe dans `app/tasks/models.py` mais est encore
> en cours de conception ; il n'est pas exposé par l'API et n'est pas documenté ici.

## Prérequis

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Docker et Docker Compose (pour la base PostgreSQL et le déploiement en conteneur)

## Installation

```bash
# installer les dépendances du projet
uv sync
```

Les paramètres sont gérés par Pydantic Settings (`app/core/config/core.py`) et se configurent via
variables d'environnement / fichiers `.env`, groupées par préfixe :

| Préfixe      | Fichier                        | Variables clefs                                                              |
| ------------ | -------------------------------- | ------------------------------------------------------------------------------- |
| _(aucun)_    | `app/core/config/core.py`        | `PROJECT_NAME`, `ENVIRONMENT` (development/production/test), `DEBUG`            |
| `AUTH_`      | `app/auth/settings.py`           | `SECRET_KEY` (alias `JWT_SECRET_KEY`), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| `DATABASE_`  | `app/db/settings.py`             | `TYPE` (postgresql/sqlite), `SERVER`, `PORT`, `USER`, `PASSWORD`, `NAME`, `FILENAME`, `ECHO`, `URL` |
| `LOG_`       | `app/core/config/logging.py`     | `LEVEL` (DEBUG/INFO/WARNING/CRITICAL)                                            |
| `CORS_`      | `app/core/config/cors.py`        | `ALLOW_ORIGINS`, `ALLOW_CREDENTIALS`, `ALLOW_METHODS`, `ALLOW_HEADERS`           |

`.env.dev` (utilisé par `docker-compose.override.yml` pour le service `api`) contient la
configuration de développement. `tests/.env` (SQLite) et `.env.test` (PostgreSQL, service
`db-test`) contiennent la configuration utilisée respectivement par les fixtures `engine`/`session`
et `client`/`auth_client` des tests.

## Lancer le projet en développement

```bash
docker compose up
# ou, via justfile:
just start
```

`docker-compose.override.yml` est fusionné automatiquement par Docker Compose et ajoute le
service `api` (rechargement à chaud) et une base `db-test` dédiée aux tests d'intégration, en
plus de `db` (PostgreSQL) et `adminer` définis dans `docker-compose.yml`.

L'API est alors disponible sur `http://localhost:8000`, avec la documentation interactive sur
`/docs` (Swagger) et `/redoc` en dehors de l'environnement `production`. Un client
[Adminer](https://www.adminer.org/) est exposé sur `http://localhost:8080` pour explorer la base
PostgreSQL.

## Base de données et migrations

Les migrations de schéma sont gérées avec Alembic. `alembic/env.py` construit dynamiquement l'URL
de connexion à partir des settings de l'application (`DatabaseSettings`), il n'y a donc rien à
configurer séparément dans `alembic.ini`.

```bash
# créer une nouvelle révision après modification d'un models.py
just makemigrations "message décrivant le changement"
# équivalent à: uv run alembic revision --autogenerate -m "message"

# appliquer les migrations
just migrate
# équivalent à: uv run alembic upgrade head
```

## Tests

```bash
uv run pytest
```

## Qualité de code

```bash
# linter et formatter
uv run ruff check .
uv run ruff format .

# vérification de types
uvx pyright .
```

## Commandes utiles (justfile)

| Commande                      | Description                                              |
| ------------------------------ | ------------------------------------------------------------ |
| `just start`                   | démarre l'app et ses dépendances via docker compose           |
| `just test [args]`              | lance la suite de tests pytest                                |
| `just lint`                     | lance `ruff check .`                                          |
| `just format`                   | lance `ruff check --fix .` puis `ruff format .`                |
| `just makemigrations "msg"`     | crée une révision Alembic (autogenerate)                       |
| `just migrate`                  | applique les migrations (`alembic upgrade head`)                |
| `just clean`                    | supprime les fichiers générés (`__pycache__`, `*.pyc`)          |
