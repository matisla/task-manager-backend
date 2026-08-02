# TODO

Sujets identifiés lors de l'alignement du projet sur la doc de référence FastAPI
(Notion > Base de connaissances > Python > FastAPI), volontairement différés : ce sont des
changements de stack ou de stratégie de test, pas des corrections d'alignement ponctuelles.

## Migration vers `structlog`

La doc de référence préconise des logs structurés via `structlog`, avec un pipeline de
`processors` et une intégration `contextvars` permettant de corréler automatiquement tous les
logs d'une requête via un `request_id`, sans avoir à le repasser explicitement en paramètre à
travers les couches (service, repository, etc.).

Le projet utilise actuellement `logging` standard, configuré via `logging.config.dictConfig`
à partir d'un fichier YAML (`app/config/logging.py` + `env/logging.yaml`/`tests/logging.yaml`).
Ce chantier est différé car il est orthogonal à l'alignement architectural en cours et
remplacerait entièrement le pipeline de logging existant : nouvelle dépendance, réécriture de
`app/config/logging.py`, et changement de tous les call sites `logging.getLogger(__name__)`
à travers l'application.

## Tests asynchrones (`httpx.AsyncClient` + `ASGITransport`)

La doc de référence préconise des tests utilisant `httpx.AsyncClient` avec `ASGITransport`,
combinés à un `app.dependency_overrides` sur `get_session` qui ouvre une transaction par test
et la annule (rollback) à la fin, garantissant une isolation totale entre tests.

Le projet utilise actuellement `fastapi.testclient.TestClient` (synchrone) avec des fixtures
`session`/`client` à portée `session` (partagées sur toute la suite) pointant vers un fichier
SQLite persistant (`tests/database.db`). Ce chantier est différé car le setup actuel fonctionne
et migrer impliquerait une refonte complète de `tests/conftest.py` (fixtures, isolation par
test) alors que `pytest-asyncio` est déjà présent en dépendance mais inutilisé pour cet usage.

## i18n (gettext/babel)

La doc de référence préconise que les exceptions métier portent une **clé** de message
(jamais le texte final), traduite à la frontière (exception handler) via `gettext`/`babel`
plutôt que dans le service.

Aucune infrastructure de traduction n'existe actuellement dans le projet — pas de besoin
identifié à ce jour de réponses API multilingues (le CLAUDE.md du projet impose déjà anglais
pour le code et français pour les échanges humains, ce qui ne se traduit pas directement en
besoin d'i18n côté API). Portée approximative si entrepris : dépendance `babel`/`gettext`,
structure de catalogue de messages (`locales/`), et branchement de la traduction sur
`AppError.detail` (voir `app/core/exceptions.py`) au niveau du handler central.
