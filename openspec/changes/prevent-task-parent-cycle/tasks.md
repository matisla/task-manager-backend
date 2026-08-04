Pas de migration Alembic nécessaire : `parent_id` existe déjà comme colonne sur `Task`
(`app/tasks/models.py`), aucune modification de `models.py` dans ce changement.

## 1. Schéma

- [ ] 1.1 Ajouter `TaskParentUpdate` à `app/tasks/schemas.py` avec un seul champ,
      `parent_id: uuid.UUID | None = None` — champ omis dans le formulaire ou envoyé vide →
      effacement du parent, champ fourni → affectation.

## 2. Service

- [ ] 2.1 Dans `app/tasks/services.py`, ajouter la constante de module
      `MAX_PARENT_DEPTH: int = 64` (même emplacement que `ALLOWED_TRANSITIONS`).

- [ ] 2.2 Dans `app/tasks/services.py`, ajouter `TaskService.reparent(session, task, parent_id)` :
      - `parent_id == task.parent_id` (y compris `None == None`, déjà pas de parent) → no-op,
        retourner `task` inchangée, sans toucher `updated_at` (pas de requête supplémentaire
        nécessaire).
      - `parent_id is None` → effacer le parent, persister via `TaskRepository.update(task,
        parent_id=None, updated_at=datetime.now(UTC))` et retourner.
      - `parent_id == task.id` → lever `ConflictError` (auto-parentage).
      - sinon résoudre le parent cible via `get_owned_or_404` (404 si absent ou non détenu par le
        même utilisateur que `task` — ne vérifie que ce parent immédiat, pas le reste de la
        chaîne, cf. design.md - Ownership à travers la chaîne d'ancêtres).
      - remonter depuis le parent cible via `parent_id`, jusqu'à `MAX_PARENT_DEPTH` niveaux, à la
        recherche de `task.id` :
        - si trouvé → lever `ConflictError` (créerait un cycle).
        - si `MAX_PARENT_DEPTH` est atteint sans trouver `task.id` → lever `AppError` (500,
          protection contre une donnée déjà corrompue, cf. design.md - Risques).
      - sinon persister le nouveau `parent_id` via `TaskRepository.update(task, parent_id=...,
        updated_at=datetime.now(UTC))` et retourner la tâche.

## 3. Router

- [ ] 3.1 Ajouter `POST /tasks/{task_id}/parent` à `app/tasks/router.py`, corps
      `Annotated[TaskParentUpdate, Form()]` (même convention que `create_task`) : résout la tâche
      via `TaskService.get_owned_or_404`, appelle `TaskService.reparent(session, task,
      data.parent_id)`, retourne `TaskRead`.

## 4. Tests

Dans `tests/tasks/`, en utilisant `TaskFactory` et les fixtures existantes (`client`, `session`,
`current_user`) :

- [ ] 4.1 Reparenter une tâche vers une tâche existante non liée → `200`, `parent_id` mis à jour.
- [ ] 4.2 Effacer le parent d'une tâche (`parent_id` omis du formulaire) → `200`, `parent_id`
      vaut `None`.
- [ ] 4.3 Reparenter une tâche vers son parent actuel → `200`, pas d'erreur, `parent_id`
      inchangé.
- [ ] 4.4 Définir une tâche comme son propre parent → `409`, `parent_id` inchangé.
- [ ] 4.5 Définir le parent d'une tâche comme l'un de ses enfants directs → `409`, `parent_id`
      inchangé.
- [ ] 4.6 Définir le parent d'une tâche comme un descendant à plusieurs niveaux (petit-enfant ou
      plus loin) → `409`, `parent_id` inchangé.
- [ ] 4.7 Définir le parent d'un ancêtre X comme un descendant D d'une tâche A située plus bas
      dans la même branche (X → A → B → D, avec X ≠ A) → `409`, `parent_id` de X inchangé. Ce
      test documente explicitement le contrat « toute la descendance » (cf. spec.md, scénario
      « Un descendant ne peut pas devenir le parent d'un ancêtre ») — il exerce le même chemin de
      code que 4.6 (même fonction `reparent`, même boucle de parcours, juste une profondeur
      différente), ce n'est pas une couverture de code supplémentaire, mais une garantie du
      contrat qu'on ne veut pas voir supprimer par erreur en la croyant redondante.
- [ ] 4.8 Reparenter une tâche qui n'existe pas, ou qui n'appartient pas à l'utilisateur
      demandeur → `404`.
- [ ] 4.9 Reparenter vers un parent cible qui n'existe pas, ou qui n'appartient pas à
      l'utilisateur demandeur → `404`.
- [ ] 4.10 Reparenter une tâche vers une tâche existante non liée (cas 4.1) → `updated_at` de la
       tâche modifiée est renseigné (non `None`) après l'appel.
- [ ] 4.11 Effacer le parent d'une tâche (cas 4.2) → `updated_at` de la tâche modifiée est
       renseigné (non `None`) après l'appel.
- [ ] 4.12 Reparenter une tâche vers son parent actuel (cas 4.3, no-op) → `updated_at` reste
       `None` (ou sa valeur précédente) après l'appel.

## 5. Contrôles qualité

- [ ] 5.1 `uv run pytest` passe, y compris les nouveaux tests et la suite existante
      `tests/tasks/` (pas de régression).
- [ ] 5.2 `uvx ruff check` et `uvx ruff format --check` passent sur les fichiers modifiés.
