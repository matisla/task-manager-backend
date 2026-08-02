# Spec : Cycle de vie du statut des Task

**Statut** : Prête pour implémentation
**Date** : 2026-07-31
**Brainstorm** : [docs/brainstorms/2026-07-31-task-status-lifecycle.md](../brainstorms/2026-07-31-task-status-lifecycle.md)

## Contexte

`Task.status` (`app/tasks/models.py`) compte aujourd'hui 6 valeurs (`BACKLOG`, `PAUSED`,
`WAITING`, `PLANNED`, `IN_PROGRESS`, `DONE`) sans aucune règle de transition : le champ est
posé à la création et jamais modifié ensuite (aucun endpoint ne le fait évoluer). Cette spec
introduit deux nouveaux statuts (`CANCELLED`, `ARCHIVED`), un graphe complet de transitions
validées côté service, un endpoint générique pour les déclencher explicitement, et une révision
de `DELETE /tasks/{id}` qui devient une suppression logique dans la majorité des cas.

## Objectif

- Ajouter `CANCELLED` et `ARCHIVED` à l'enum `Status` de `Task`.
- Faire respecter le graphe de transitions validé dans le brainstorm, avec rejet explicite
  (`HTTPException`) de toute transition non autorisée.
- Exposer un endpoint `POST /tasks/{id}/{status}` pour déclencher les transitions explicites.
- Réviser `DELETE /tasks/{id}` pour appliquer la règle à trois branches (suppression physique,
  archivage implicite, ou refus).
- Fixer automatiquement `completed_at` lors du passage à `DONE`.
- Exposer le champ `status` dans `TaskRead` (actuellement absent du schéma de sortie).
- Garantir qu'une Task ne peut être lue, transitionnée ou supprimée que par son propriétaire.

## Non-objectifs

- Tout ce qui concerne `Routine` (table non encore migrée, router/service inexistants) : le
  mécanisme de delta (création/annulation automatique de Task selon la RRULE), le champ
  `Task.routine_id`, et le graphe `RoutineStatus` sont traités par une spec dédiée ultérieure.
- Un endpoint générique d'édition de contenu (`PATCH /tasks/{id}` pour `title`, `description`,
  `due_date`, etc.) et la pose du marqueur « détaché » (`updated_at` non nul) qui en découle :
  hors périmètre, traité par une future spec. Cette spec-ci garantit seulement que les
  transitions de statut ne posent **pas** ce marqueur (cf. Q5 du brainstorm).
- Historique/audit des transitions (table de log) — voir Proposition.
- Possibilité de créer une Task directement à un statut autre que `BACKLOG` via l'API : la
  création reste inchangée (`Task.status` par défaut, non paramétrable dans `TaskCreate`).

## Design détaillé

### 1. Enum `Status` — `app/tasks/models.py`

Ajout de deux membres, avec le même style de commentaire inline que l'existant :

```python
class Status(str, Enum):
    BACKLOG = "backlog"
    PAUSED = "paused"
    WAITING = "waiting"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"  # abandoned, failure or user decision
    ARCHIVED = "archived"  # hidden from frontend, kept in database
```

### 2. Graphe de transitions — `app/tasks/services.py`

Le graphe est porté par une constante au niveau module, pas par la classe `Status` elle-même
(garde la logique métier dans `services.py`, conformément à la convention du projet) :

```python
ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.BACKLOG: frozenset({Status.PLANNED, Status.CANCELLED}),
    Status.PLANNED: frozenset({Status.BACKLOG, Status.IN_PROGRESS, Status.CANCELLED}),
    Status.IN_PROGRESS: frozenset(
        {Status.PAUSED, Status.WAITING, Status.DONE, Status.CANCELLED}
    ),
    Status.PAUSED: frozenset({Status.IN_PROGRESS, Status.WAITING, Status.CANCELLED}),
    Status.WAITING: frozenset({Status.IN_PROGRESS, Status.PAUSED, Status.CANCELLED}),
    Status.DONE: frozenset({Status.ARCHIVED}),
    Status.CANCELLED: frozenset({Status.ARCHIVED}),
    Status.ARCHIVED: frozenset(),  # terminal, no outgoing transition
}
```

Aucune boucle sur soi-même (`X → X`) n'est définie : re-poster le statut courant est traité
comme une transition invalide (cf. Cas limites).

### 3. `TaskService` — `app/tasks/services.py`

Remplace le `TaskService` actuel (squelette non fonctionnel, docstring copiée de `User`) :

```python
class TaskService:
    """
    Service handling task lifecycle: ownership resolution, status transitions and deletion.
    """

    @classmethod
    def get_owned_or_404(cls, session: Session, task_id: uuid.UUID, user: User) -> Task:
        """
        Retrieve a task by id, scoped to its owner.

        Args:
            session (Session): session used to access the database.
            task_id (uuid.UUID): id of the task to retrieve.
            user (User): the requesting user, expected to own the task.

        Raises:
            HTTPException: 404 if the task does not exist or is not owned by the user.

        Returns:
            Task: the retrieved task.
        """

    @classmethod
    def transition(cls, session: Session, task: Task, target: Status) -> Task:
        """
        Move a task to a new status, validated against ALLOWED_TRANSITIONS.

        Args:
            session (Session): session used to access the database.
            task (Task): task to transition.
            target (Status): the requested target status.

        Raises:
            HTTPException: 409 if the transition is not allowed from the current status.

        Returns:
            Task: the updated task.
        """
        # if target == Status.DONE: task.completed_at = datetime.now(UTC)
        # updated_at is intentionally left untouched (cf. Non-objectifs / brainstorm Q5)

    @classmethod
    def delete(cls, session: Session, task: Task) -> Task | None:
        """
        Apply the three-branch deletion rule.

        - BACKLOG: physical delete, returns None.
        - DONE / CANCELLED: implicit transition to ARCHIVED, returns the task.
        - ARCHIVED: idempotent no-op, returns the task unchanged (cf. Cas limites).
        - any other status: raises HTTPException 409.

        Args:
            session (Session): session used to access the database.
            task (Task): task to delete.

        Raises:
            HTTPException: 409 if the task is neither BACKLOG, DONE, CANCELLED nor ARCHIVED.

        Returns:
            Task | None: the archived task, or None if physically deleted.
        """
```

`get_owned_or_404` centralise une vérification absente aujourd'hui : `detail_task` et
`delete_task` appellent `session.get(Task, task_id)` sans filtrer par `user_id`, ce qui permet
à n'importe quel utilisateur authentifié d'accéder à ou de supprimer la Task d'un autre
utilisateur en devinant son UUID. Comme les nouveaux endpoints de transition opèrent sur une
Task précise, cette vérification devient indispensable ; on en profite pour l'appliquer aussi
aux deux endpoints existants (correction d'un trou de sécurité préexistant, pas une extension de
périmètre fonctionnel).

### 4. Router — `app/tasks/router.py`

- Nouvel endpoint :

  ```python
  @router.post("/{task_id}/{target_status}", response_model=TaskRead)
  async def transition_task(
      task_id: uuid.UUID,
      target_status: Status,
      user: currentUserDep,
      session: SessionDep,
  ):
      ...
  ```

  `target_status: Status` en tant que paramètre de chemin est validé automatiquement par
  FastAPI/Pydantic (valeur hors enum → `422` natif, pas de code à écrire).

- `detail_task` et `delete_task` utilisent désormais `TaskService.get_owned_or_404`.
- `delete_task` appelle `TaskService.delete` : si le retour est `None` → `204` (déjà le
  comportement actuel) ; si une `Task` est retournée (cas `ARCHIVED`) → `204` également (le
  contrat HTTP de `DELETE` ne change pas pour l'appelant, que la suppression soit physique ou
  logique).

### 5. Schéma — `app/tasks/schemas.py`

Ajout du champ manquant à `TaskRead` :

```python
class TaskRead(TaskBase):
    ...
    status: Status
```

### 6. Migration Alembic

`Status` est mappé en `sa.Enum` natif nommé `"status"` (cf.
`alembic/versions/f132464c5630_initial_migration.py`). Ajouter des membres à cet enum a un
comportement différent selon le moteur :

- **SQLite** (tests) : `sa.Enum` y est émulé en `VARCHAR` + `CHECK` constraint ; `autogenerate`
  ne détecte pas fiablement l'ajout de valeurs à un enum existant.
- **PostgreSQL** (dev/prod) : type `ENUM` natif ; `autogenerate` ne génère **rien** pour un ajout
  de valeur — il faut écrire à la main `op.execute("ALTER TYPE status ADD VALUE 'cancelled'")`
  (et `'archived'`), et s'assurer que ces `ALTER TYPE ... ADD VALUE` ne s'exécutent pas dans le
  même bloc transactionnel que d'autres opérations DDL sur ce type (limitation PostgreSQL) —
  utiliser `with op.get_context().autocommit_block():` si Alembic groupe la migration dans une
  transaction.

Conformément à la convention du projet (CLAUDE.md, section Migrations), la révision sera
proposée à l'utilisateur dans la même tâche que la modification de `models.py`, générée via
`uv run alembic revision --autogenerate -m "add cancelled and archived status to task"`, puis
relue et corrigée manuellement pour les points ci-dessus avant d'être considérée terminée.
`alembic upgrade head` ne sera pas exécuté sans confirmation explicite.

## Plan d'implémentation

1. `app/tasks/models.py` : ajouter `CANCELLED` et `ARCHIVED` à `Status`.
2. `app/tasks/services.py` : le fichier actuel importe `from .models import User` et
   `from .schemas import Token, UserCreate`, qui n'existent ni l'un ni l'autre dans
   `app/tasks/models.py`/`schemas.py` (copié depuis `app/auth/services.py` sans adaptation) —
   le module casse dès son import. Le réécrire entièrement : imports corrigés, suppression du
   `RoutineService` placeholder (hors périmètre, cf. Non-objectifs), et `TaskService` avec
   `get_owned_or_404`, `transition`, `delete`.
3. `app/tasks/schemas.py` : ajouter `status: Status` à `TaskRead`.
4. `app/tasks/router.py` : ajouter `POST /{task_id}/{target_status}` ; faire passer
   `detail_task` et `delete_task` par `TaskService.get_owned_or_404` / `TaskService.delete`.
5. Proposer et générer la révision Alembic (`uv run alembic revision --autogenerate -m "add
   cancelled and archived status to task"`), relire et corriger le fichier généré (cf. Design
   détaillé §6).
6. Tests (`tests/tasks/test_task.py` ou nouveau `tests/tasks/test_task_lifecycle.py`) — voir
   Plan de tests.
7. `uv run pytest`, `uvx ruff check`, `uvx ruff format --check`.

## Critères d'acceptation

- [x] `Status` expose `CANCELLED` et `ARCHIVED`.
- [x] `POST /tasks/{id}/{status}` accepte une transition définie dans `ALLOWED_TRANSITIONS` et
      retourne `200` avec la `Task` mise à jour (`response_model=TaskRead`, `status` inclus).
- [x] `POST /tasks/{id}/{status}` refuse (`409`) toute transition absente du graphe, y compris
      une transition vers le statut courant.
- [x] `IN_PROGRESS → DONE` fixe `completed_at` ; aucune autre transition ne le modifie.
- [x] Aucune transition (explicite ou implicite) ne modifie `updated_at`.
- [x] `DELETE /tasks/{id}` sur une Task `BACKLOG` : suppression physique (ligne absente en
      base après l'appel).
- [x] `DELETE /tasks/{id}` sur une Task `DONE` ou `CANCELLED` : la ligne persiste en base avec
      `status == ARCHIVED`, réponse `204`.
- [x] `DELETE /tasks/{id}` sur une Task `ARCHIVED` : `204`, aucun changement d'état (idempotent).
- [x] `DELETE /tasks/{id}` sur toute autre Task (`PLANNED`, `IN_PROGRESS`, `PAUSED`, `WAITING`) :
      `409`, aucune modification en base.
- [x] `GET /tasks/{id}`, `DELETE /tasks/{id}`, `POST /tasks/{id}/{status}` retournent `404` si la
      Task n'existe pas ou n'appartient pas à l'utilisateur authentifié.
- [x] `uv run pytest` et `uvx ruff check` passent sans erreur (sur le périmètre de cette spec ;
      voir Feedback pour les erreurs `ruff check`/`ruff format` préexistantes hors périmètre).

## Impacts & Risques

- **Sécurité** : correction d'un trou d'autorisation préexistant (`detail_task`/`delete_task`
  ne filtraient pas par propriétaire) — comportement plus strict, pas de régression attendue
  côté clients légitimes puisqu'ils n'accédaient déjà qu'à leurs propres tâches via le flux
  normal.
- **Migration** : ajout de valeurs à un `ENUM` PostgreSQL natif — nécessite une révision Alembic
  écrite/corrigée à la main (voir Design détaillé §6), pas une simple validation de l'autogenerate.
- **Compatibilité** : `TaskRead` gagne un champ (`status`) — additif, non cassant pour des
  clients JSON existants. `DELETE /tasks/{id}` change de comportement pour les statuts autres
  que `BACKLOG`/`DONE`/`CANCELLED` (nouveau `409` là où l'opération réussissait silencieusement
  avant) — c'est un changement de comportement intentionnel de cette spec, à mentionner si un
  frontend existant dépend du succès inconditionnel du `DELETE`.
- **Code mort à nettoyer** : `app/tasks/services.py` casse dès son import (`from .models import
  User` et `from .schemas import Token, UserCreate` n'existent pas dans ce module) — la
  réécriture prévue à l'étape 2 du plan résout ce point au passage, ce n'est pas une régression
  introduite par cette spec.

## Cas limites et gestion d'erreurs

- **Transition vers le statut courant** (`X → X`) : non définie dans `ALLOWED_TRANSITIONS` →
  rejetée (`409`), pas traitée comme un no-op silencieux.
- **`DELETE` sur une Task déjà `ARCHIVED`** : la règle à trois branches du brainstorm ne couvre
  explicitement que `BACKLOG` et `{DONE, CANCELLED}` ; `ARCHIVED` est traité ici comme un
  quatrième cas idempotent (`204` sans effet), `ARCHIVED` représentant déjà l'équivalent d'une
  suppression logique. **Point à confirmer avec l'utilisateur en review** — c'est une extension
  raisonnable mais non explicitement tranchée dans le brainstorm.
- **`target_status` invalide dans l'URL** (valeur hors enum, ex. `/tasks/{id}/foo`) : `422`
  natif FastAPI, aucune validation manuelle nécessaire.
- **Transition depuis `ARCHIVED`** : couverte par le graphe (`frozenset()` vide) → toujours
  `409`, cohérent avec son caractère terminal.
- **Task inexistante ou appartenant à un autre utilisateur** : `404` identique dans les deux cas
  (ne pas distinguer « n'existe pas » de « appartient à quelqu'un d'autre » pour ne pas confirmer
  l'existence d'un UUID à un utilisateur non autorisé).

## Plan de tests

Dans `tests/tasks/`, en s'appuyant sur `TaskFactory` et les fixtures existantes
(`client`, `session`, `current_user`) :

- Transitions valides : au moins un test par arête du graphe (paramétré), vérifiant le `200` et
  le `status` retourné.
- Transitions invalides : au moins un test par statut terminal/source (`ARCHIVED → *`,
  `DONE → PLANNED`, `X → X`), vérifiant le `409`.
- `IN_PROGRESS → DONE` : vérifie que `completed_at` est renseigné après la transition et reste
  `None` pour tout autre statut.
- Toute transition testée : vérifie que `updated_at` reste `None` après l'appel.
- `DELETE` : un test par branche (`BACKLOG` → ligne absente en base ; `DONE`/`CANCELLED` → ligne
  présente avec `status == ARCHIVED` ; `ARCHIVED` → `204` sans changement ; `PLANNED`/
  `IN_PROGRESS`/`PAUSED`/`WAITING` → `409`).
- Autorisation : `GET`, `DELETE` et `POST .../{status}` sur une Task appartenant à un autre
  utilisateur retournent `404` (nécessite de créer un deuxième utilisateur/token dans le test).
- Régression : les tests existants de `test_task.py` (`test_create_task`, `test_list_tasks`,
  `test_delete_task`) continuent de passer sans modification.

## Proposition

- Historique des transitions (table `task_status_history` ou équivalent) si un futur besoin
  d'audit ou d'affichage de timeline apparaît — non nécessaire aujourd'hui.
- Une fois la spec Routine reprise : réutiliser `ALLOWED_TRANSITIONS`/`TaskService.transition`
  comme modèle pour `RoutineStatus` et `POST /routines/{id}/{status}`.
- Endpoint `PATCH /tasks/{id}` pour l'édition de contenu, posant le marqueur « détaché »
  (`updated_at`) évoqué dans le brainstorm — prérequis pour le mécanisme de delta côté Routine.
