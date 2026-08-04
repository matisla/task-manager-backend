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

- Ajout de `PATCH /tasks/{id}` pour changer (ou effacer) le `parent_id` d'une tâche après sa
  création. C'est le même endpoint que celui envisagé pour la future édition générale de contenu
  (`title`, `description`, `due_date`, ...) déjà signalée dans
  `docs/specs/01-task-status-lifecycle.md`, mais ce changement-ci ne câble que le champ
  `parent_id` — les champs de contenu et le marqueur « detached » qu'ils déclenchent restent hors
  périmètre et seront ajoutés au même endpoint par une future spec. Quand le payload contiendra à
  la fois `parent_id` et des champs de contenu, le reparentage sera traité en premier (avant tout
  autre champ) : une tentative de cycle rejette la requête entière avant que d'autres champs ne
  soient appliqués.
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
  `TaskService`), `app/tasks/router.py` (nouvel endpoint `PATCH /tasks/{id}`),
  `app/tasks/schemas.py` (schéma de requête pour le nouvel endpoint, limité à `parent_id` pour
  l'instant mais destiné à être étendu par la future spec d'édition de contenu),
  `app/tasks/repository.py` (requête pour parcourir la chaîne parent/descendant, si non
  réalisable avec les relations déjà chargées).
- **API** : additif — nouvel endpoint `PATCH /tasks/{id}`, aucun changement sur les endpoints
  existants. Cet endpoint sera réutilisé (et étendu) par la future spec d'édition de contenu
  plutôt que d'en créer un second.
- **Performance** : la validation anti-cycle nécessite de parcourir la chaîne d'ancêtres du
  parent candidat (ou l'arbre des descendants de la tâche déplacée) à chaque appel de
  reparentage ; la profondeur est bornée par le niveau d'imbrication réel des tâches des
  utilisateurs, censé rester faible, mais la stratégie de parcours (requête récursive vs.
  parcours itératif en Python) est une décision de conception.
- **Prépare** la future spec générale d'édition de contenu (title/description/due_date et le
  marqueur « detached ») sans l'anticiper : elle réutilisera le même `PATCH /tasks/{id}` et le
  même schéma `TaskUpdate` en y ajoutant des champs, plutôt que de créer son propre endpoint.
- **Migration** : aucune migration Alembic n'est nécessaire. `parent_id` existe déjà comme colonne
  sur `Task` (`app/tasks/models.py`) ; ce changement ne modifie pas `models.py`.

## À Clarifier

Points relevés en revue, non tranchés par les décisions ci-dessus :

- **Encodage du payload de `PATCH /tasks/{id}`** : JSON ou `Form()` (convention actuelle de
  `create_task`, cf. `app/tasks/router.py`) ? Le choix conditionne comment un client peut effacer
  `parent_id` (valeur `null` explicite) — un formulaire encodé (`application/x-www-form-urlencoded`)
  n'a pas de représentation native pour un `null` sur un champ `UUID`, ce qui est pourtant le
  scénario « Effacer le parent d'une tâche » de `specs/task-reparenting/spec.md`.
- **Cardinalité de `parent_id` dans `TaskUpdate`** : champ obligatoire pour l'instant (pas de
  valeur par défaut). À réévaluer quand la future édition de contenu ajoutera des champs
  optionnels au même schéma, pour distinguer « champ absent du payload » de « champ explicitement
  remis à `null` » (problème classique des mises à jour partielles).
- **Concurrence (TOCTOU)** : le parcours de la chaîne d'ancêtres lit l'état de la hiérarchie au
  moment de la requête, sans verrou. Deux reparentages concurrents sur des branches qui
  s'entrecroisent pourraient chacun passer la validation avant que l'autre ne committe, et
  introduire un cycle à deux. Probablement acceptable vu l'usage mono-utilisateur attendu, mais
  non tranché explicitement.
- **Couverture du test « ancêtre / descendant d'un tiers »** (tasks.md 4.7) : exerce le même
  chemin de code que le test « descendant multi-niveaux » (4.6), l'algorithme ne faisant aucune
  distinction entre « la tâche directement reparentée » et un nœud plus loin dans la hiérarchie —
  utile comme documentation vivante du contrat, mais n'ajoute pas de couverture de code
  supplémentaire.
