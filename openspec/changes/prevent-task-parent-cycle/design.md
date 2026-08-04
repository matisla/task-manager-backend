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
- L'édition générale du contenu des tâches (`title`, `description`, `due_date` via un futur
  `PATCH /tasks/{id}`) et le marqueur « detached » qu'elle poserait — spec future séparée, selon
  la proposition. Ce changement-ci introduit un endpoint dédié au reparentage
  (`POST /tasks/{id}/parent`), indépendant de ce futur endpoint.
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

- `POST /tasks/{task_id}/parent`, corps `Form()` — un nouveau schéma `TaskParentUpdate` dans
  `app/tasks/schemas.py` avec un seul champ, `parent_id: uuid.UUID | None = None`. Endpoint dédié
  (pas de partage avec le futur `PATCH /tasks/{id}` d'édition de contenu), à la manière de
  `POST /tasks/{id}/{status}` déjà en place pour les transitions de statut — cohérent avec la
  convention `Form()` du router.
- Le défaut `None` sur `parent_id` couvre à la fois « champ omis » et « champ explicitement remis
  à vide » de façon indifférenciée, ce qui est correct ici : l'endpoint n'a qu'un seul objet
  (fixer ou effacer le parent), il n'y a jamais de troisième état « ne pas toucher ce champ » à
  distinguer, contrairement à une mise à jour partielle multi-champs.
- Réutilise `TaskRead` comme modèle de réponse, comme pour l'endpoint de transition.

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
- **[Risque]** Le parcours anti-cycle lit l'état de la hiérarchie au moment de la requête, sans
  verrou : deux reparentages concurrents sur des branches qui s'entrecroisent (ex. `A → parent B`
  et `B → parent A` soumis quasi simultanément) pourraient chacun passer la validation avant que
  l'autre ne committe, et introduire un cycle à deux une fois les deux commits appliqués →
  **Mitigation** : acceptée sans mécanisme dédié, vu l'usage attendu (un utilisateur, un client à
  la fois, actions issues d'une UI séquentielle) qui rend la fenêtre de course étroite ; à revoir
  (verrouillage `SELECT ... FOR UPDATE`, ou isolation `SERIALIZABLE`) si un usage multi-client
  concurrent sur la même hiérarchie apparaît.
- **[Compromis]** Un endpoint dédié `POST /tasks/{id}/parent` (plutôt que d'intégrer ceci dans un
  futur `PATCH /tasks/{id}` général) signifie que deux endpoints de mutation de tâche existeront
  une fois le `PATCH` général livré → accepté pour éviter de bloquer ce changement sur une spec
  d'édition de contenu non planifiée, et pour éviter l'ambiguïté d'encodage `Form()`/JSON qu'un
  endpoint partagé aurait introduite sur l'effacement de `parent_id` (voir proposal.md - À
  Clarifier, point résolu).
