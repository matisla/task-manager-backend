## Pourquoi

`Task` prend déjà en charge une hiérarchie parent/enfant (`parent_id`, relations `parent`/
`children` auto-référencées dans `app/tasks/models.py`), mais la seule façon de définir
`parent_id` aujourd'hui est à la création (`TaskCreate.parent_id`), où un cycle est
structurellement impossible — une tâche tout juste créée ne peut pas déjà être l'ancêtre de quoi
que ce soit. Il n'existe actuellement aucun moyen de changer le parent d'une tâche après sa
création, donc le risque de cycle noté dans `docs/backlog.md` est latent, pas exploitable.

Ce changement introduit la capacité manquante — déplacer une tâche sous un autre parent — et la
livre en même temps que le garde-fou anti-cycle, de sorte que l'endpoint de reparentage n'est
jamais exposé sans la validation qui le rend sûr. Construire le garde-fou seul d'abord ajouterait
du code mort, sans chemin atteignable pour l'exercer de bout en bout.

## Ce qui change

- Ajout de `POST /tasks/{id}/parent` pour changer (ou effacer) le `parent_id` d'une tâche après sa
  création. Endpoint dédié, à la manière de `POST /tasks/{id}/{status}` déjà en place pour les
  transitions de statut — cohérent avec la convention `Form()` du router
  (`app/tasks/router.py`) et sans ambiguïté d'encodage : `parent_id: uuid.UUID | None = None`,
  champ omis dans le formulaire → effacement du parent, champ fourni → affectation. La future
  édition générale de contenu (`title`, `description`, `due_date`, et le marqueur « detached »
  qu'elle poserait), déjà signalée dans `docs/specs/01-task-status-lifecycle.md`, reste un
  `PATCH /tasks/{id}` entièrement séparé, non entamé par ce changement.
- Ajout de la validation anti-cycle dans `TaskService`, appliquée à chaque affectation de parent :
  - une tâche ne peut pas être définie comme son propre parent.
  - plus généralement : ni la tâche, ni les enfants de la tâche, ne peuvent apparaître comme étant
    parent de la tâche elle-même ou de l'un de ses parents — à quelque profondeur que ce soit dans
    la hiérarchie. Une seule vérification implémente cette garantie : le nouveau parent proposé ne
    doit pas se retrouver, en remontant sa propre chaîne de parents, sur la tâche déplacée. Comme
    cette vérification est appliquée identiquement à chaque appel de reparentage, quelle que soit
    la tâche concernée, elle couvre aussi le cas où un ancêtre X serait reparenté sous un
    descendant D d'une tâche A : rejeté par la même règle, car D est aussi un descendant de X.
  - le parcours de la chaîne est plafonné par une constante globale `MAX_PARENT_DEPTH = 64` (dans
    `app/tasks/services.py`, même emplacement que `ALLOWED_TRANSITIONS`), pour se prémunir contre
    une boucle infinie si un cycle existait déjà en base malgré cette validation (donnée corrompue
    en dehors de l'API). Hors périmètre de ce changement, mais à noter : rendre cette limite
    configurable via `settings` plutôt qu'une constante en dur, si le besoin apparaît.
- Rejet des tentatives de reparentage invalides avec une erreur explicite (`ConflictError` →
  `409`), cohérent avec la façon dont les transitions de statut invalides sont rejetées
  aujourd'hui.
- Vérification de propriété : le parent cible doit appartenir à l'utilisateur demandeur, même
  règle que celle déjà appliquée par `TaskService.get_owned_or_404` à la tâche modifiée. Cette
  vérification ne porte que sur le parent cible immédiat, pas sur le reste de la chaîne
  d'ancêtres : un parent et un enfant peuvent appartenir à des utilisateurs différents, ce n'est
  pas une anomalie à corriger par ce changement.
- Mise à jour de `updated_at` : seule la tâche identifiée par `task_id` (celle modifiée par la
  requête) voit son `updated_at` mis à jour, et uniquement lorsque `parent_id` change réellement
  (affectation ou effacement) ; les autres tâches consultées pendant la validation (parent cible,
  ancêtres traversés) restent inchangées. Un reparentage no-op (vers le parent déjà courant)
  laisse `updated_at` intact, cohérent avec le fait que la tâche est retournée « inchangée ».

## Capacités

### Nouvelles capacités

- `task-reparenting` : changer le parent d'une tâche après sa création, y compris la validation
  empêchant les cycles parent/enfant dans la hiérarchie des tâches.

### Capacités modifiées

_Aucune — aucune capacité `openspec/specs/` existante ne couvre aujourd'hui la hiérarchie des
tâches._

## Impact

- **Code** : `app/tasks/services.py` (nouvelle validation + logique de reparentage dans
  `TaskService`), `app/tasks/router.py` (nouvel endpoint `POST /tasks/{id}/parent`),
  `app/tasks/schemas.py` (schéma de requête dédié pour le nouvel endpoint),
  `app/tasks/repository.py` (requête pour parcourir la chaîne parent/descendant, si non
  réalisable avec les relations déjà chargées).
- **API** : additif — nouvel endpoint `POST /tasks/{id}/parent`, aucun changement sur les
  endpoints existants. Indépendant du futur `PATCH /tasks/{id}` d'édition de contenu, qui restera
  un endpoint séparé.
- **Performance** : la validation anti-cycle nécessite de parcourir la chaîne d'ancêtres du
  parent candidat (ou l'arbre des descendants de la tâche déplacée) à chaque appel de
  reparentage ; la profondeur est bornée par le niveau d'imbrication réel des tâches des
  utilisateurs, censé rester faible, mais la stratégie de parcours (requête récursive vs.
  parcours itératif en Python) est une décision de conception.
- **Migration** : aucune migration Alembic n'est nécessaire. `parent_id` existe déjà comme colonne
  sur `Task` (`app/tasks/models.py`) ; ce changement ne modifie pas `models.py`.

## À Clarifier

_Aucun point restant — tous les points relevés en revue ont été tranchés (voir historique des
décisions dans `design.md`)._
