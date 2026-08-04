## Contexte

`Task.parent_id` est une clé étrangère auto-référencée (`app/tasks/models.py`), avec les
relations SQLModel `parent`/`children` déjà déclarées. Aucune relation ni index ne permet
aujourd'hui de remonter la chaîne d'ancêtres efficacement — une recherche dans la chaîne signifie
suivre `parent_id` une ligne à la fois. L'application tourne sur PostgreSQL, ce qui limite dans
quelle mesure on peut s'appuyer sur une syntaxe de requête récursive spécifique à la base de
données.

Voir `proposal.md` - Pourquoi pour la motivation, et `specs/task-reparenting/spec.md` pour le
contrat de comportement exact.

## Objectifs / Non-objectifs

**Objectifs :**
- Décider comment la vérification ancêtre/descendant est implémentée (stratégie de requête).
- Décider où vit la vérification (`TaskService`, selon la convention du projet consistant à
  garder la logique métier hors des routers/repositories) et ce qu'elle retourne/lève.
- Définir la forme requête/réponse du nouvel endpoint.

**Non-objectifs :**
- L'édition générale du contenu des tâches (`title`, `description`, `due_date` via le même
  `PATCH /tasks/{id}`) et le marqueur « detached » qu'elle poserait — spec future séparée, selon
  la proposition. Ce changement-ci pose l'endpoint et n'y câble que `parent_id`.
- L'optimisation du parcours pour des hiérarchies très profondes (des centaines de niveaux) —
  hors périmètre étant donné l'usage attendu (hiérarchies de tâches personnelles, une poignée de
  niveaux tout au plus).

## Décisions

### Stratégie de parcours : parcours itératif en Python, pas de CTE SQL récursive

Pour vérifier si définir le parent de la tâche A comme la tâche B créerait un cycle, on remonte
depuis B via `parent_id` (B → B.parent → B.parent.parent → ...) à la recherche de A. Si A est
trouvé, B est un descendant de A et le déplacement est rejeté.

- **Choisi** : boucle itérative dans `TaskService`, un appel `session.get`/repository par niveau,
  borné par un garde-fou de profondeur maximale (voir Risques).
- **Alternative envisagée** : CTE `WITH RECURSIVE` dans `TaskRepository` — une seule requête au
  lieu de N, mais la syntaxe des CTE récursives et la prise en charge de la détection de cycle
  diffèrent entre PostgreSQL et l'émulation SQLite, ajoutant une charge de maintenance à double
  moteur pour une vérification qui s'exécute sur des données peu profondes (arbres de tâches
  personnelles, pas des organigrammes profonds). À revoir si les hiérarchies s'avèrent assez
  profondes pour que le parcours en N requêtes pose problème en pratique.
- La logique métier reste dans `TaskService`, cohérent avec la convention du projet (`CLAUDE.md`)
  consistant à garder les règles métier hors de `repository.py`.
- Cette même vérification, appliquée identiquement à chaque appel de `reparent` quelle que soit la
  tâche passée en argument, garantit la propriété plus générale demandée : ni une tâche ni aucun
  de ses descendants ne peut devenir le parent de cette tâche ou de l'un de ses ancêtres. Aucune
  logique dédiée supplémentaire n'est nécessaire — reparenter un ancêtre X sous un descendant D
  d'une tâche A est rejeté par la même règle, car D est aussi un descendant de X (voir
  `specs/task-reparenting/spec.md`, scénario « Un descendant ne peut pas devenir le parent d'un
  ancêtre »).

### Ownership à travers la chaîne d'ancêtres : non garantie, et ce n'est pas un problème

Seul le parent cible immédiat est vérifié comme appartenant au même utilisateur que la tâche
déplacée (via `get_owned_or_404`). Le reste de la chaîne, traversé par le parcours anti-cycle, n'est
pas re-filtré par propriétaire — un parent et un enfant peuvent appartenir à des utilisateurs
différents (cf. `docs/backlog.md`, section « Gestion des permissions et attribution », qui envisage
l'assignation de tâches entre utilisateurs). Ce n'est donc pas une anomalie à corriger par ce
changement, y compris pour `TaskCreate.parent_id` qui ne vérifie pas non plus l'ownership à la
création (`app/tasks/services.py`, `TaskService.create`) : comportement existant, inchangé ici.

### `updated_at` : mis à jour uniquement sur la tâche modifiée, uniquement si `parent_id` change réellement

Contrairement aux transitions de statut (`TaskService.transition`, qui laissent volontairement
`updated_at` intact, cf. `docs/specs/01-task-status-lifecycle.md`), un reparentage effectif (via
`TaskService.reparent`, quand `parent_id` est affecté ou effacé) met à jour `updated_at` de la
tâche identifiée par `task_id`. Le cas no-op (reparentage vers le parent déjà courant) ne modifie
rien, `updated_at` compris, cohérent avec le fait que la tâche est retournée inchangée. Les autres
tâches lues pendant la validation (parent cible, ancêtres traversés) ne sont jamais persistées et
ne voient donc jamais leur `updated_at` changer.

### Où s'exécute la vérification : une méthode `TaskService` appelée avant la persistance du nouveau parent

`TaskService.reparent(session, task, new_parent_id)` — reprend le modèle existant de
`TaskService.transition` (valider par rapport à une règle, lever `ConflictError` en cas de
violation, sinon persister via `TaskRepository.update`). Résout et vérifie la propriété du parent
cible via le `get_owned_or_404` existant, puis effectue le parcours d'ancêtres, puis met à jour.

### Endpoint et schéma

- `PATCH /tasks/{task_id}`, corps `{"parent_id": uuid.UUID | None}` — un nouveau schéma
  `TaskUpdate` dans `app/tasks/schemas.py`. C'est le schéma qui portera aussi les futurs champs de
  contenu (`title`, `description`, `due_date`) lorsque cette spec-là sera implémentée ; il n'expose
  pour l'instant que `parent_id`, pour éviter d'avoir à renommer le schéma ou l'endpoint à ce
  moment-là.
- Réutilise `TaskRead` comme modèle de réponse, comme pour l'endpoint de transition.

### Ordre de traitement des champs dans `PATCH /tasks/{task_id}`

Le reparentage (validation du cycle incluse) est traité avant tout autre champ du payload. Pour ce
changement-ci, `parent_id` est le seul champ existant donc l'ordre n'a pas d'effet observable —
mais il est fixé maintenant pour que la future spec d'édition de contenu n'ait pas à revenir sur
cette décision : quand `title`/`description`/`due_date` rejoindront le même payload, un
reparentage invalide (cycle, self-parent) devra rejeter la requête entière (`409`) avant que les
autres champs ne soient appliqués, plutôt que d'appliquer partiellement les changements. Le
handler du router (ou `TaskService`) appelle donc `reparent` en premier lorsque `parent_id` est
présent dans le payload, avant tout traitement des autres champs.

## Risques / Compromis

- **[Risque]** Le parcours itératif fait O(profondeur) allers-retours base de données par appel
  de reparentage → **Mitigation** : acceptable étant donné la profondeur attendue faible
  (proposal.md - Impact) ; à revoir avec une CTE si les données d'usage montrent plus tard des
  hiérarchies profondes.
- **[Risque]** Un bug dans le parcours (ou des données corrompues en dehors de l'API, par ex.
  édition directe en base) pourrait boucler indéfiniment si un cycle existait déjà sans être
  détecté → **Mitigation** : plafonner le parcours via une constante globale
  `MAX_PARENT_DEPTH = 64` dans `app/tasks/services.py` (même emplacement que
  `ALLOWED_TRANSITIONS`) et lever une erreur interne (`AppError`, 500) si la profondeur est
  dépassée sans trouver la tâche déplacée, plutôt que de boucler sans limite. Hors périmètre de ce
  changement, mais à noter pour une itération future : exposer cette limite comme un paramètre de
  `settings` (`pydantic-settings`) plutôt qu'une constante en dur, si le besoin de l'ajuster
  apparaît.
- **[Compromis]** Réutiliser `PATCH /tasks/{id}` maintenant, avant que la spec d'édition de
  contenu n'existe, signifie que le schéma `TaskUpdate` et le comportement de l'endpoint devront
  être étendus (pas recréés) par cette future spec → accepté pour éviter qu'un second endpoint de
  mutation de contenu (`PATCH /tasks/{id}/parent` distinct) ne coexiste inutilement avec le futur
  endpoint général une fois celui-ci livré.
