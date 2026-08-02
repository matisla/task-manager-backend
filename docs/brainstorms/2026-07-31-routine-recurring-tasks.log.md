# Log : Routine (générateur de tâches récurrentes)

**Brainstorm** : [`2026-07-31-routine-recurring-tasks.md`](./2026-07-31-routine-recurring-tasks.md)

<details>
<summary>Q1 - Mécanisme de génération des Task — Mécanisme de génération</summary>

**Thème :** Mécanisme de génération
**Question posée :** Comment une `Routine` déclenche-t-elle la création de ses `Task` ?
**Choix proposés :** Lazy à la lecture ; job planifié (cron/scheduler) ; hybride (lazy +
endpoint explicite de génération).
**Décision :** Lazy à la lecture. Pas de scheduler/worker à introduire pour l'instant ;
le calcul se fait au moment d'une action backend plutôt qu'en tâche de fond.

</details>

<details>
<summary>Q2 - Déclencheur exact du renouvellement — Déclencheur de renouvellement</summary>

**Thème :** Déclencheur de renouvellement
**Question posée :** Qu'est-ce qui déclenche concrètement la création de la Task
suivante ?
**Choix proposés :** Question ouverte, pas d'options fermées proposées.
**Décision :** La complétion de la Task courante générée par la Routine (pas un
`GET /tasks` générique). Une seule Task ouverte par Routine à la fois. Pour
AFTER_COMPLETED, `start_date` passe à `now()`. Pour FIXED_SCHEDULE non bornée,
`start_date` passe à la prochaine occurrence RRULE future, en ignorant les occurrences
manquées entre-temps (une Task en retard reste simplement ouverte, l'alerte de retard
étant un problème d'affichage frontend). Pour FIXED_SCHEDULE bornée (COUNT/UNTIL connu),
toutes les Task sont créées d'un coup à la création de la Routine, sans mécanisme lazy.

</details>

<details>
<summary>Q3 - Lien entre Task et Routine — Lien Task ↔ Routine</summary>

**Thème :** Lien Task ↔ Routine
**Question posée :** Comment une Task générée par une Routine est-elle reliée à
celle-ci ?
**Choix proposés :** Question ouverte, pas d'options fermées proposées.
**Décision :** Nouveau champ `Task.routine_id: uuid.UUID | None`, séparé de `parent_id`
(qui reste dédié aux sous-tâches).

</details>

<details>
<summary>Q4 - Garantie "une seule Task ouverte par Routine" — Portée de la règle "une seule Task ouverte à la fois"</summary>

**Thème :** Portée de la règle "une seule Task ouverte à la fois"
**Question posée :** Comment garantir qu'une Routine lazy n'a jamais plus d'une Task
ouverte à la fois ? Vérification service vs contrainte DB.
**Choix proposés :** Vérification au niveau service (levée d'erreur métier) ; contrainte
DB.
**Décision :** Cette règle ne s'applique qu'aux Routines lazy (AFTER_COMPLETED,
FIXED_SCHEDULE non bornée) — pour une FIXED_SCHEDULE bornée, plusieurs Task ouvertes
simultanément est normal et sans risque (générées en une fois, indépendantes ensuite).
Pour le cas lazy, la règle doit être vérifiée explicitement au niveau service (pas de
contrainte DB), avec levée d'une erreur si l'invariant est violé. Le flux attendu est de
fermer la Task courante avant d'en ouvrir une nouvelle.
**Pourquoi :** Avoir 2 Task ouvertes en même temps serait une erreur pouvant provoquer
des effets de bord.

</details>

<details>
<summary>Q5 - Start_date / due_date dans le passé — Due_date dans le passé (FIXED_SCHEDULE)</summary>

**Thème :** Due_date dans le passé (FIXED_SCHEDULE)
**Question posée :** Pour une Routine FIXED_SCHEDULE bornée avec `start_date` dans le
passé (ex: 5 occurrences dont 3 déjà passées à la création), que fait-on des occurrences
déjà passées ?
**Choix proposés :** Tout créer (dont en retard) ; ne créer que le futur ; refuser la
création.
**Décision (v1) :** Refuser la création si `start_date` est dans le passé.
**Correction :** Ce n'est pas `start_date` en tant que tel qui pose problème (une
`start_date` passée dont la prochaine occurrence RRULE tombe dans le futur est valide).
L'erreur porte sur la tentative de création d'une Task dont la `due_date` serait déjà
dans le passé — c'est ce cas précis qui est refusé, que ce soit en génération batch
(bornée) ou lazy.

</details>

<details>
<summary>Q6 - Modification de la RRULE / recurrency_type après coup — Modification de la RRULE / recurrency_type après coup</summary>

**Thème :** Modification de la RRULE / recurrency_type après coup
**Question posée :** Que se passe-t-il si la RRULE ou le `recurrency_type` d'une Routine
est modifié après coup, alors que des Task ont déjà été générées à partir de l'ancienne
configuration ?
**Choix proposés :** Interdire la modification ; l'autoriser avec effet sur le futur
seulement ; autoriser avec recalcul complet.
**Décision :** La modification est autorisée. Direction retenue à ce stade (à valider en
pratique) : supprimer les Task déjà générées par la Routine et les recréer selon la
nouvelle RRULE, sauf celles ayant un `updated_at` non nul (protégées car modifiées
manuellement par l'utilisateur après génération — on ne veut pas écraser une édition
manuelle). Une piste alternative à base de calcul de delta entre l'existant et la
nouvelle liste théorique a été envisagée mais jugée plus complexe, non retenue comme
approche principale à ce stade.
**Note :** cette réponse a depuis été remplacée par le calcul de delta (option 1 de
Q10), tranché dans le brainstorm
[`2026-07-31-task-status-lifecycle.md`](2026-07-31-task-status-lifecycle.md) (Q3) — voir
la section "Modification de la RRULE / recurrency_type après coup" du fichier principal
pour l'état actuel.

</details>

<details>
<summary>Q7 - Transition UNDEFINED → ACTIVE et gestion des statuts — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** Le passage `UNDEFINED` → `ACTIVE` doit-il être explicite (action
dédiée de l'utilisateur) ou automatique dès que la config de récurrence est valide ?
**Choix proposés :** Explicite (action dédiée) ; automatique dès que la configuration de
récurrence est valide.
**Décision :** Explicite dans tous les cas, jamais en effet de bord d'une autre action.
Exception ajoutée : `ACTIVE` peut être demandé dès la création (via le payload), à
condition que les conditions du statut cible soient remplies, sinon la création échoue.
Décision complémentaire (élargit le sujet à `Task`) : les transitions de statut
post-création passent par un endpoint dédié `POST /{resource}/{id}/{status}` (`routines`
et `tasks`) plutôt qu'un `PATCH` générique sur `status`, avec validation des conditions
de la transition côté service (`services.py`) et erreur explicite si les conditions ne
sont pas remplies.
**Note :** cette réponse a été partiellement corrigée en Q9 — les transitions de statut
ne sont finalement pas toujours explicites, une transition implicite en effet de bord
reste possible.

</details>

<details>
<summary>Q8 - Graphe complet des transitions de statut de Routine — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** Quel est le graphe complet des transitions autorisées pour
`RoutineStatus` (`UNDEFINED`, `ACTIVE`, `INACTIVE`, `ARCHIVED`), avec leurs conditions ?
**Choix proposés :** Question ouverte, pas d'options fermées proposées.
**Décision :**
- `UNDEFINED → ACTIVE` : `start_date` définie (passé ou futur indifférent), aucune Task
  à créer avec `due_date` déjà passée, type/valeurs de récurrence cohérents.
- `ACTIVE → ARCHIVED` : autorisé seulement si toutes les Task liées sont `DONE` ou
  supprimées (aucune Task ouverte restante).
- `ACTIVE → INACTIVE` : autorisé seulement si aucune Task ouverte ne reste liée à la
  Routine.
- `INACTIVE → ARCHIVED` : toujours autorisé (par construction, plus aucune Task ouverte
  à ce stade).
- `ARCHIVED` : terminal, aucune transition sortante.
**Note :** restaient ouvertes à ce stade le mécanisme exact de `ACTIVE → INACTIVE` (que
faire si une Task ouverte est supprimée directement plutôt que complétée ?) et les
conditions de `INACTIVE → ACTIVE` — précisées en Q9.

</details>

<details>
<summary>Q9 - Suppression d'une Task ouverte liée à une Routine ACTIVE — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** Si l'utilisateur supprime directement la Task ouverte courante
d'une Routine `ACTIVE`, que se passe-t-il ?
**Choix proposés :** Bascule implicite en `INACTIVE` ; suppression refusée ; génération
immédiate de la Task suivante.
**Décision :** Si après suppression il reste au moins une Task ouverte liée à la Routine
(cas d'une Routine bornée à plusieurs Task ouvertes simultanément), la Routine reste
`ACTIVE`. Si la suppression fait tomber le nombre de Task ouvertes à zéro, la Routine
bascule automatiquement en `INACTIVE`. `INACTIVE → ACTIVE` (réactivation) recalcule et
crée les Task manquantes par un calcul de delta, sans regénération naïve de tout
l'historique — sémantique exacte précisée en Q10.
**Pourquoi :** Correction de Q7 — les transitions de statut ne sont donc pas toujours
explicites, une transition peut être déclenchée implicitement en effet de bord d'une
autre action. Ces effets de bord implicites devront être bien couverts par les tests.

</details>

<details>
<summary>Q10 - Critère d'identité entre Task existante et Task candidate (calcul de delta) — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** Pour le calcul de delta (réactivation `INACTIVE → ACTIVE`, et
modification de RRULE cf. Q6), quel critère permet de dire qu'une Task existante A "est
la même" qu'une occurrence théorique candidate B (et donc que B ne doit pas être
créée) ?
**Choix proposés :**
1. Clé naturelle `(routine_id, due_date)` : deux Task sont la même occurrence si même
   Routine et même `due_date`. Combiné à un statut `Task.CANCELLED` plutôt qu'une
   suppression physique (idée soulevée en aparté par l'utilisateur), ce critère suffit à
   empêcher la recréation d'une occurrence volontairement annulée.
2. Index d'occurrence (position dans la séquence RRULE) stocké sur la Task : plus
   robuste face à une `due_date` modifiée manuellement sur une Task détachée, mais
   nécessite un nouveau champ et un calcul d'index à chaque génération.
3. Fenêtre de tolérance sur `due_date` (ex: ±1 jour) en complément de (1), utile
   seulement si des écarts d'arrondi RRULE/timezone sont observés en pratique.
**Décision :** Non tranchée à ce stade dans cette session — recommandation formulée :
option 1 combinée à un statut `CANCELLED` sur `Task`.
**Note :** cette recommandation a depuis été retenue comme décision finale, tranchée
dans le brainstorm
[`2026-07-31-task-status-lifecycle.md`](2026-07-31-task-status-lifecycle.md) (Q3) — voir
la section "Modification de la RRULE / recurrency_type après coup" du fichier principal
pour l'état actuel.

</details>

<details>
<summary>Q11 - Déclencheur de ACTIVE → INACTIVE après le delete à 3 branches — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** `TaskService.delete` refuse désormais (`409`) la suppression d'une
Task ouverte non-`BACKLOG` (cas normal d'une Task générée par Routine, plutôt
`PLANNED`), ce qui rend quasi impossible le scénario "suppression directe" prévu en Q9
pour déclencher `ACTIVE → INACTIVE`. Comment redéfinir ce déclencheur ?
**Choix proposés :**
1. Le déclencheur devient toute transition faisant sortir la Task du périmètre
   "ouverte" (`CANCELLED` ou suppression physique résiduelle `BACKLOG`), les deux
   déclenchant le même recalcul du nombre de Task ouvertes.
2. Seul le passage en `CANCELLED` compte comme déclencheur.
3. Flux explicite obligatoire en deux étapes (`CANCELLED` puis `DELETE`), sans
   transition implicite automatique.
**Décision :** Inversion de la causalité par rapport à Q9 — ce n'est plus un changement
d'état des Task qui déclenche implicitement `ACTIVE → INACTIVE`, mais l'inverse : la
désactivation d'une Routine (`ACTIVE → INACTIVE`) est une action **explicite**, dont
l'effet de bord est de faire passer automatiquement en `CANCELLED` toutes les Task
ouvertes encore liées à la Routine (utilise la transition `CANCELLED` déjà autorisée
depuis tout statut ouvert, sans passer par `TaskService.delete`).
**Pourquoi :** Évite le conflit avec la règle à trois branches de `TaskService.delete`
(qui refuse la suppression d'une Task ouverte non-`BACKLOG`) en ne s'appuyant plus sur
une suppression du tout — la Routine pilote directement le statut de ses Task via une
transition déjà existante et toujours permise.
**Note :** un warning sera affiché côté frontend, avant de procéder, si les Task
associées à la Routine sont dans un statut autre que `PLANNED` — validation UX
uniquement, pas un blocage côté backend.

</details>

<details>
<summary>Q12 - Transitions UNDEFINED → INACTIVE / UNDEFINED → ARCHIVED — Cycle de vie et transitions de statut (Routine et Task)</summary>

**Thème :** Cycle de vie et transitions de statut (Routine et Task)
**Question posée :** Une Routine `UNDEFINED` n'a jamais généré de Task. Faut-il
autoriser `UNDEFINED → INACTIVE` et `UNDEFINED → ARCHIVED` directement ?
**Choix proposés :**
1. Les deux interdites : `INACTIVE`/`ARCHIVED` n'ont de sens qu'après un passage par
   `ACTIVE`.
2. Les deux autorisées sans condition : rien à nettoyer, rien ne s'y oppose
   techniquement.
3. Autoriser seulement `UNDEFINED → ARCHIVED` (abandon sans activation), interdire
   `UNDEFINED → INACTIVE`.
**Décision :** Option 1 — les deux transitions sont interdites depuis `UNDEFINED`.
**Pourquoi :** `INACTIVE` et `ARCHIVED` n'ont de sens que comme des états atteints après
avoir été `ACTIVE` au moins une fois ; une Routine jamais activée reste `UNDEFINED`
jusqu'à son activation (la suppression physique reste possible, mais hors sujet du
graphe de statut).

</details>

<details>
<summary>Q13 - Correction du bug bloquant dans _check_recurrence_config — Modèle de données (Routine)</summary>

**Thème :** Modèle de données (Routine)
**Question posée :** `_check_recurrence_config` compare `start_date` et `interval_days`
à `None`, alors que les deux champs ont des valeurs par défaut non-`None`
(`default_factory=now()` et `default=0`) — aucune `Routine` ne peut donc être créée avec
succès actuellement. Correction recommandée : rendre les deux champs optionnels
(`datetime | None`, `int | None`). Question annexe : `interval_days` doit-il rester
valide à `0` (`gt=-1` actuel) ou exiger un minimum d'1 jour (`gt=0`) ?
**Choix proposés :**
1. Nullabilité + `gt=0` (minimum 1 jour, `0` invalide).
2. Nullabilité + `gt=-1` conservé (`0` reste valide).
3. Autre approche de correction du bug.
**Décision :** Option 2 — `start_date` et `interval_days` deviennent optionnels
(`datetime | None = None`, `int | None = None`) pour corriger le bug de comparaison à
`None`, et la contrainte reste `0` inclus comme borne basse valide pour `interval_days`
(`ge=0`, équivalent à l'actuel `gt=-1`, pas de minimum à 1 jour).

</details>

<details>
<summary>Q14 - Alerte "occurrences sautées" (FIXED_SCHEDULE non bornée) — Déclencheur de renouvellement</summary>

**Thème :** Déclencheur de renouvellement
**Question posée :** Quand `update_start_date` avance `start_date` à la prochaine
occurrence RRULE strictement future, les occurrences intermédiaires manquées sont
ignorées silencieusement — comment concevoir une alerte qui le signale à
l'utilisateur ?
**Choix proposés :**
1. Champ simple sur `Routine` (ex. `last_skipped_at: datetime | None`), mis à jour par
   le service, exposé dans `RoutineRead`, affiché par le frontend.
2. Table d'audit dédiée enregistrant chaque événement de saut.
3. Calcul à la volée à chaque lecture, sans persistance.
**Décision :** Hors périmètre backend — entièrement traité côté frontend, aucun champ
ni mécanisme à prévoir côté API/modèle pour cette alerte.

</details>

<details>
<summary>Q15 - Endpoints à exposer pour Routine — Endpoints Routine</summary>

**Thème :** Endpoints Routine
**Question posée :** Au-delà de `POST /routines/{id}/{status}` (déjà décidé), quelle
surface d'API prévoir pour `Routine` ?
**Choix proposés :**
1. CRUD standard aligné sur `Task` (`POST`, `GET` liste, `GET` détail,
   `POST /{id}/{status}`), sans endpoint de génération manuelle.
2. CRUD standard + endpoint explicite de génération manuelle
   (`POST /routines/{id}/generate`).
3. CRUD standard + endpoint de prévisualisation des prochaines occurrences théoriques
   (`GET /routines/{id}/preview`), sans matérialiser de Task.
**Décision :** Option 1 — CRUD standard aligné sur `Task`, sans endpoint de génération
manuelle ni de prévisualisation à ce stade.
**Pourquoi :** Le mécanisme lazy suffit ; un endpoint de génération manuelle ajouterait
un second chemin de création de Task à maintenir en cohérence avec les invariants déjà
actés (une seule Task ouverte, delta sur `INACTIVE → ACTIVE`), sans besoin exprimé.
**Note :** l'utilisateur demande explicitement d'être resollicité plus tard pour
revalider l'ensemble complet des routes `Routine`, une fois le reste du sujet figé —
action différée à ne pas oublier avant de considérer ce thème terminé.

</details>

<details>
<summary>Q16 - Création de la toute première Task d'une Routine — Déclencheur de renouvellement</summary>

**Thème :** Déclencheur de renouvellement
**Question posée :** Le déclencheur de génération documenté (Q2) est uniquement "la
complétion de la Task courante" — mais à la toute première activation, il n'y a pas
encore de Task à compléter. Quel mécanisme crée la première Task ?
**Choix proposés :** Question ouverte, soulevée en préparant `docs/prépare/routine_impl.md`.
**Décision :** La première Task est créée dès que la Routine atteint le statut `ACTIVE`
pour la première fois, que ce soit via la transition explicite `UNDEFINED → ACTIVE`, ou
directement à la création si `ACTIVE` est demandé dès le payload (cf. Q7) — dans les
deux cas, à condition que la validation passe (aucune Task à `due_date` déjà passée,
config de récurrence cohérente, etc., cf. Q8).

</details>

<details>
<summary>Q17 - start_date pour AFTER_COMPLETED — Modèle de données (Routine)</summary>

**Thème :** Modèle de données (Routine)
**Question posée :** Q8 pose "`start_date` définie" comme condition générique de
`UNDEFINED → ACTIVE` — mais le modèle interdit actuellement `start_date` d'être défini
pour `AFTER_COMPLETED` (seul `interval_days` l'est). Faut-il lever cette interdiction ?
**Choix proposés :** Question ouverte, soulevée en préparant `docs/prépare/routine_impl.md`.
**Décision :** `start_date` doit être accepté pour `AFTER_COMPLETED` également — il sert
d'ancre pour la `due_date` de la toute première Task (avant toute complétion, cf. Q16),
avant d'être écrasé par `now()` à chaque complétion suivante comme déjà décidé (Q2). La
condition générique de Q8 ("`start_date` définie") était donc correcte telle quelle ; la
correction porte sur `_check_recurrence_config` côté modèle, dont la branche
`AFTER_COMPLETED` ne doit plus interdire `start_date` (seul `recurrency_rule` reste
interdit pour cette stratégie).

</details>
