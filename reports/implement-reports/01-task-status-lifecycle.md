# Rapport d'implémentation : Cycle de vie du statut des Task

**Spec** : [docs/specs/01-task-status-lifecycle.md](../../docs/specs/01-task-status-lifecycle.md)
**Date** : 2026-08-01

## Description

Ajout de `CANCELLED`/`ARCHIVED` à `Status`, réécriture complète de `TaskService`
(`get_owned_or_404`, `transition`, `delete`) avec le graphe `ALLOWED_TRANSITIONS`, nouvel
endpoint `POST /tasks/{id}/{status}`, révision de `DELETE /tasks/{id}` (règle à trois
branches), ajout de `status` à `TaskRead`, et sécurisation par propriétaire de
`detail_task`/`delete_task`. Révision Alembic `bfa492dd7b5b` ajoutée pour les deux nouvelles
valeurs d'enum.

## Feedback

- **`app/tasks/services.py` était effectivement cassé** dès l'import (`from .models import
  User`, `from .schemas import Token, UserCreate` inexistants), conforme au diagnostic de la
  spec — réécriture complète sans incident.
- **Génération Alembic bloquée par l'environnement local**, sans rapport avec cette spec :
  `alembic/env.py` importe `config.get_settings()`, qui exige un `logging.yaml` à la racine
  (absent — seul `env/logging.yaml`, copié dans l'image Docker au build, existe) et, une fois
  contourné via `LOG_CONFIG_FILE=tests/logging.yaml`, la commande `--autogenerate` doit de
  toute façon se connecter à la base Postgres, qui n'est joignable que depuis le réseau Docker
  (`db` n'expose pas de port host dans `docker-compose.yml`). La révision a donc été écrite à
  la main plutôt que générée, en suivant exactement le format attendu par la spec (§6) :
  `ALTER TYPE status ADD VALUE` dans un `autocommit_block()`, gardé par un test de dialecte
  pour ne rien exécuter côté SQLite. **Point à vérifier** : la relire dans un environnement où
  `alembic revision --autogenerate` peut réellement tourner contre Postgres, pour confirmer
  qu'elle correspond à ce qu'aurait produit l'outil.
- **La spec ne prévoit pas d'exposer `completed_at` dans `TaskRead`** (seul `status` est
  ajouté au schéma, cf. Design détaillé §5) — le plan de tests demandait de vérifier
  `completed_at` après transition ; ceci a donc été vérifié en relisant l'objet en base plutôt
  que via le corps de la réponse JSON. Écart mineur entre le plan de tests (qui ne précise pas
  la source de vérité) et le design détaillé, résolu sans ambiguïté par la lecture du schéma.
- **Piège SQLAlchemy dans les tests** : vérifier `session.get(Task, task.id) is None` après
  `session.expire_all()` échoue si `task` a été supprimée côté serveur — accéder à `task.id`
  sur une instance expirée déclenche un rechargement de la ligne (qui n'existe plus). Corrigé
  en capturant `task_id = task.id` avant l'appel `DELETE`.

## Évaluation

Tous les critères d'acceptation de la spec sont satisfaits (cases cochées dans le fichier de
spec). Couverture par fichier modifié/créé :

| Fichier | Test |
|---|---|
| `app/tasks/models.py` (enum `Status`) | `test_task_lifecycle.py` (transitions paramétrées couvrant chaque membre) |
| `app/tasks/services.py` (réécrit) | `test_task_lifecycle.py` (toutes les méthodes de `TaskService`) |
| `app/tasks/schemas.py` (`status` sur `TaskRead`) | `test_task_lifecycle.py::test_valid_transition` (assertion sur `status` dans la réponse) |
| `app/tasks/router.py` (nouvel endpoint + sécurisation) | `test_task_lifecycle.py` (endpoint transition, tests 404 propriétaire) |
| `alembic/versions/bfa492dd7b5b_...py` | non testé automatiquement (nécessite Postgres, cf. Feedback) |
| `tests/tasks/test_task_lifecycle.py` (nouveau) | s'auto-couvre |

`uv run pytest` : 85 tests passés (aucune régression sur `test_task.py`/`test_jwt.py`).
`uvx ruff check`/`ruff format --check` : aucune erreur sur les fichiers touchés par cette
spec ; des erreurs préexistantes et hors périmètre subsistent ailleurs (`app/auth/models.py`,
la partie `Routine` non commitée de `app/tasks/models.py`, `app/asgi.py`,
`app/config/core.py`, `tests/auth/test_jwt.py`, `tests/tasks/test_task.py`) — non introduites
par cette implémentation.

## Proposition

- Rejouer/valider la révision Alembic `bfa492dd7b5b` dans un environnement avec accès à
  Postgres (`alembic upgrade head` reste à confirmer explicitement avec l'utilisateur avant
  exécution, conformément au CLAUDE.md du projet).
- Envisager de documenter/fixer la config locale de logging (`logging.yaml` manquant à la
  racine hors Docker) pour que `alembic revision --autogenerate` fonctionne directement en
  local — hors périmètre de cette spec.
