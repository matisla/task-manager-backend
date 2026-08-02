# Brainstorm : Routine (générateur de tâches récurrentes)

**Log** : [`2026-07-31-routine-recurring-tasks.log.md`](./2026-07-31-routine-recurring-tasks.log.md)

## Contexte

Ajout d'une entité `Routine` dans `app/tasks/` servant de générateur de `Task` pour les
actions qui se répètent dans le temps. Le modèle `Routine` existe déjà (non commité) dans
`app/tasks/models.py`, avec deux stratégies de récurrence : `FIXED_SCHEDULE` (règle RRULE,
RFC 5545) et `AFTER_COMPLETED` (intervalle en jours depuis la dernière complétion). Rien
n'existe encore côté `router.py` ni `schemas.py` pour `Routine`, et `Task` n'a pas encore de
lien vers `Routine` (champ `routine_id` toujours à ajouter).

**Mise à jour suite à l'implémentation de
[`01-task-status-lifecycle.md`](../specs/01-task-status-lifecycle.md)** : le cycle de vie de
`Task.status` évoqué plus bas comme prérequis est maintenant **implémenté** (et non plus
seulement planifié) — `CANCELLED`/`ARCHIVED` ajoutés à l'enum, graphe `ALLOWED_TRANSITIONS` et
`TaskService.transition`/`TaskService.delete` fonctionnels dans `app/tasks/services.py`,
endpoint `POST /tasks/{id}/{status}` exposé, migration Alembic dédiée créée. Au passage,
l'ancien stub `RoutineService` (qui cassait l'import du module, cf. bug noté en "En cours") a
été **supprimé entièrement** de `services.py` plutôt que corrigé — hors périmètre de cette
spec. `RoutineService` est donc à reconstruire de zéro pour reprendre ce sujet, en s'inspirant
du pattern `TaskService` (`get_owned_or_404`, `transition`, `delete`, constante
`ALLOWED_TRANSITIONS`) comme le suggère explicitement la section "Proposition" de la spec.

## Décisions

### Mécanisme de génération

Génération **lazy** : pas de scheduler ni de worker. Le calcul "une nouvelle occurrence
est-elle due ?" est déclenché lors d'une action côté backend (ex: lecture des tâches,
ou action explicite), et la `Task` correspondante est créée à ce moment-là si nécessaire.
Pas de nouvelle brique d'infra (cron/Celery) à introduire pour l'instant. (voir Q1)

### Modèle de données (Routine)

`start_date` et `interval_days` doivent être **optionnels** au niveau du modèle
(`datetime | None = None`, `int | None = None`) — le bug bloquant actuel de
`_check_recurrence_config` vient de leurs valeurs par défaut non-`None`
(`default_factory=now()` et `default=0`), qui empêchent toute création de `Routine` quelle
que soit la stratégie. `interval_days` reste valide à `0` (`ge=0`, pas de minimum à 1 jour).

`start_date` est accepté (et pertinent) pour **les deux** stratégies de récurrence, pas
seulement `FIXED_SCHEDULE` : il sert d'ancre pour la `due_date` de la toute première Task
générée par la Routine (cf. "Déclencheur de renouvellement" ci-dessous), avant d'être écrasé
par `now()` à chaque complétion suivante côté `AFTER_COMPLETED`. La branche `AFTER_COMPLETED`
de `_check_recurrence_config` ne doit donc plus interdire `start_date` — seul
`recurrency_rule` reste interdit pour cette stratégie. La condition générique de
`UNDEFINED → ACTIVE` ("`start_date` définie", cf. graphe plus bas) s'applique donc telle
quelle aux deux stratégies, sans distinction. (voir Q13, Q17)

### Déclencheur de renouvellement

Le déclencheur unique de génération d'une nouvelle Task (une fois la Routine `ACTIVE`) est la
**complétion de la Task courante générée par la Routine** (méthode `update_start_date`, à
recréer dans le futur `RoutineService` — l'ancien stub a été supprimé, cf. Contexte). Une
Routine n'a qu'une seule Task ouverte (non terminée) à la fois : tant qu'elle n'est pas
complétée, aucune nouvelle Task n'est générée, même si l'échéance est dépassée (la Task reste
ouverte et en retard — l'alerte de retard est un problème d'affichage frontend, pas de
génération backend).

**Cas particulier : la toute première Task.** Ce déclencheur ne s'applique qu'à partir de la
deuxième occurrence — il n'y a pas encore de Task à compléter au moment de la toute première
activation. La première Task est donc créée dès que la Routine atteint `ACTIVE` pour la
première fois, que ce soit via la transition explicite `UNDEFINED → ACTIVE`, ou directement à
la création si `ACTIVE` est demandé dès le payload (cf. Q7) — dans les deux cas, à condition
que la validation passe (aucune Task à `due_date` déjà passée, config de récurrence cohérente,
cf. Q8). Sa `due_date` initiale vient de `start_date`, pour les deux stratégies de récurrence
(cf. section "Modèle de données", `start_date` pour `AFTER_COMPLETED`).

À la complétion de la Task courante (deuxième occurrence et suivantes) :
- **AFTER_COMPLETED** : `start_date` de la Routine est mis à `now()` (date de complétion),
  la prochaine Task est due à `start_date + interval_days`.
- **FIXED_SCHEDULE non bornée** : `start_date` est avancée à la **prochaine occurrence RRULE
  strictement future** après `now()` — les occurrences intermédiaires manquées (ex: routine
  hebdomadaire complétée 3 semaines plus tard) sont ignorées, pas de rattrapage/backlog de
  Task. Alerte "occurrences sautées" traitée entièrement côté frontend (Q14), rien à prévoir
  côté backend.

(voir Q2, Q14, Q16)

### Génération FIXED_SCHEDULE bornée

Si la RRULE de la Routine est bornée (`COUNT` ou `UNTIL` défini, nombre d'occurrences connu
à l'avance), **toutes** les Task sont créées immédiatement à la création de la Routine — pas
de génération lazy dans ce cas. (voir Q2)

### Lien Task ↔ Routine

Nouveau champ `Task.routine_id: uuid.UUID | None` (FK vers `Routine.id`), distinct de
`parent_id` qui reste réservé aux sous-tâches — **toujours pas ajouté au modèle `Task`** à ce
stade. Permet de retrouver la Task ouverte d'une Routine par une requête simple (`routine_id`
+ `status not in (DONE, CANCELLED, ARCHIVED)`) : ces deux statuts sont désormais **implémentés**
sur `Task` (plus seulement anticipés), cf.
[`2026-07-31-task-status-lifecycle.md`](2026-07-31-task-status-lifecycle.md) et sa spec
[`01-task-status-lifecycle.md`](../specs/01-task-status-lifecycle.md). (voir Q3)

### Portée de la règle "une seule Task ouverte à la fois"

Cette règle ne s'applique **qu'aux Routines à génération lazy** (`AFTER_COMPLETED` et
`FIXED_SCHEDULE` non bornée). Pour une `FIXED_SCHEDULE` bornée (COUNT/UNTIL connu), toutes
les Task sont créées d'un coup et sont indépendantes ensuite : fermer l'une n'a aucun impact
sur les autres (pas de recalcul, `start_date` inchangée). Supprimer une Task terminée (ex:
via un futur `clear_finished_tasks`) ne pose pas de problème de tracking, les Task n'étant
pas autrement liées entre elles au-delà de `routine_id`.

Pour les Routines lazy, la règle est **appliquée explicitement au niveau service** (pas de
contrainte DB) : `RoutineService.update_start_date` doit vérifier qu'il n'existe pas déjà une
autre Task ouverte pour la Routine avant d'en créer une nouvelle, et lever une erreur métier
sinon (violation d'invariant plutôt qu'ignorée silencieusement). Le flux attendu est donc :
fermer la Task courante d'abord, puis seulement ensuite ouvrir la suivante. (voir Q4)

### Due_date dans le passé (FIXED_SCHEDULE)

`start_date` dans le passé n'est **pas** en soi une erreur (ex: une routine hebdomadaire dont
`start_date` tombe la semaine dernière mais dont la prochaine occurrence RRULE est dans le
futur est valide). L'erreur se produit uniquement au moment où l'on tenterait de **créer une
Task dont la `due_date` est déjà dans le passé** — c'est la création de cette Task précise qui
est refusée, pas la Routine sur la base de son `start_date`. Pour une FIXED_SCHEDULE bornée,
si une des occurrences à générer en batch tombe dans le passé, sa création échoue (et donc la
création de la Routine avec elle, vu que le batch est fait d'un coup). Ne concerne pas
AFTER_COMPLETED, qui ne s'appuie pas sur `start_date` de la même façon (cf. bug de validation
déjà noté : le modèle actuel exige que `start_date` soit `None` pour AFTER_COMPLETED). (voir Q5)

### Cycle de vie et transitions de statut (Routine et Task)

Les changements de statut (`Routine.status` et `Task.status`) sont **le plus souvent
explicites** (action dédiée de l'utilisateur), mais peuvent aussi être déclenchés
**implicitement**, en effet de bord d'une autre action métier — toujours dans le sens
Routine → Task, jamais l'inverse (ex: désactiver une Routine `ACTIVE` en `INACTIVE` fait
passer implicitement en `CANCELLED` toutes ses Task ouvertes, cf. graphe ci-dessous). Ces
transitions implicites devront être particulièrement bien couvertes par les tests (cf. Notes).

Statut par défaut à la création d'une Routine : `UNDEFINED`. Exception : il est possible de
demander explicitement `ACTIVE` dès la création (champ dans le payload de création), à
condition que les conditions du statut cible soient remplies — sinon la création échoue avec
une erreur explicite.

Pattern d'API retenu pour les transitions explicites post-création : un endpoint dédié plutôt
qu'un `PATCH` générique sur le champ `status` :
- `POST /routines/{id}/{status}` pour `Routine`
- `POST /tasks/{id}/{status}` pour `Task` (même principe, étend le sujet au-delà de `Routine`)

Chaque transition (explicite ou implicite) est validée côté service (logique d'évaluation dans
`services.py`, pas dans le routeur) : si les conditions pour atteindre le statut cible ne sont
pas remplies, une erreur métier explicite (`HTTPException`) est levée plutôt que d'accepter
silencieusement le changement.

Graphe des transitions de `Routine` :

```
UNDEFINED ──[start_date définie (passé ou futur OK) ;
             aucune Task à créer avec due_date déjà passée ;
             type/valeurs de récurrence cohérents]──▶ ACTIVE
           (aucune transition sortante vers INACTIVE/ARCHIVED
            depuis UNDEFINED)

ACTIVE ──[explicite, toujours autorisé ; effet de bord :
          toutes les Task ouvertes liées à la Routine passent
          en CANCELLED (via TaskService.transition, pas
          TaskService.delete)]──▶ INACTIVE

ACTIVE ──[explicite : toutes les Task liées sont DONE,
          CANCELLED ou ARCHIVED (aucune Task ouverte
          restante)]──▶ ARCHIVED

INACTIVE ──[explicite, toujours autorisé : par construction
            plus aucune Task ouverte à ce stade]──▶ ARCHIVED

INACTIVE ──[explicite : recalcule et crée les Task manquantes
            par delta, critère d'identité (routine_id, due_date)
            + statut CANCELLED]──▶ ACTIVE

ARCHIVED : terminal, aucune transition sortante
```

Historique : le déclencheur de `ACTIVE → INACTIVE` a été revu suite à l'implémentation de
[`01-task-status-lifecycle.md`](../specs/01-task-status-lifecycle.md), qui a rendu la
suppression physique d'une Task ouverte non-`BACKLOG` impossible (`TaskService.delete` refuse
avec `409`) — le mécanisme initialement envisagé (suppression déclenchant implicitement
`INACTIVE`) n'était donc plus applicable. La causalité a été inversée : c'est la désactivation
explicite de la Routine qui cascade sur ses Task, pas l'inverse (voir Q11).

(voir Q7, Q8, Q9, Q10, Q11, Q12)

### Modification de la RRULE / recurrency_type après coup

La modification de la configuration de récurrence d'une Routine existante est **autorisée**
(pas d'immutabilité). **Mise à jour** (tranché dans
[`2026-07-31-task-status-lifecycle.md`](2026-07-31-task-status-lifecycle.md), Q3) : l'approche
initialement envisagée ("supprimer puis recréer sauf `updated_at` non nul") est remplacée par un
calcul de delta basé sur la clé naturelle `(routine_id, due_date)` — piste qui était envisagée
comme alternative ci-dessous et finalement retenue :
- Task existante dont la `due_date` correspond à une entrée de la nouvelle liste théorique :
  conservée telle quelle, pas recréée.
- Entrée de la nouvelle liste théorique sans Task existante correspondante : nouvelle Task créée.
- Task existante dont la `due_date` ne correspond plus à aucune entrée de la nouvelle liste :
  passe automatiquement en `Task.CANCELLED` (au lieu d'être supprimée).
- **Exception inchangée** : une Task portant un `updated_at` non nul ("détachée", modifiée
  manuellement par l'utilisateur) est préservée telle quelle, jamais annulée automatiquement.

Ce même mécanisme de delta s'applique à la réactivation `INACTIVE → ACTIVE`. (voir Q6, Q10)

## En cours

- `RoutineService` a été **supprimé entièrement** de `services.py` (plutôt que corrigé) lors de
  l'implémentation de `01-task-status-lifecycle.md`, le stub cassant l'import du module (bug
  précédemment noté ici). À reconstruire de zéro pour reprendre le sujet Routine, en réutilisant
  le pattern `TaskService` (`get_owned_or_404`, `transition`, `delete`, constante
  `ALLOWED_TRANSITIONS`) — explicitement recommandé par la section "Proposition" de la spec.
- Endpoints `Routine` (CRUD standard + `POST /routines/{id}/{status}`) tranchés en Q15 — mais
  **revalidation explicitement demandée par l'utilisateur** : repasser en revue l'ensemble
  complet des routes une fois le reste du sujet figé, avant de considérer ce thème terminé.
- Migration Alembic : celle pour `CANCELLED`/`ARCHIVED` sur `Task.status` est faite. Reste à
  prévoir : nouvelle table `Routine` + FK `Task.routine_id`, et la correction du modèle
  `Routine` elle-même (`start_date`/`interval_days` optionnels, cf. "Modèle de données").
- Tests à prévoir, en particulier la couverture des transitions de statut implicites
  (cf. Décisions et Notes). Note : `tests/tasks/test_task_lifecycle.py` couvre déjà le cycle de
  vie de `Task` seule (hors Routine).

## Information complémentaire

- Conventions du projet : un service par domaine (`UserService`, `TaskService`), méthodes
  `@classmethod`, exceptions métier via `HTTPException`. `Task.get_by(session, field, value)`
  existe déjà côté `auth` pour `User` — pattern à vérifier/réutiliser si pertinent.
- `Task` supporte déjà une relation parent/enfant via `parent_id` (auto-jointure).

## Notes

- Préférence terminologique : privilégier « Task ouverte » plutôt que « Task active » pour
  désigner une Task non terminée, afin d'éviter la confusion avec le statut `ACTIVE` d'une
  `Routine`.
- Attention aux effets de bord des changements de statut implicites (ex: désactivation d'une
  Routine `ACTIVE → INACTIVE` déclenchant le passage en `CANCELLED` de ses Task ouvertes) : à
  bien couvrir par les tests.
- Le statut `CANCELLED` sur une Task (terminée mais non réalisée) est intéressant pour la
  bascule `ACTIVE → INACTIVE` d'une Routine. Idée similaire pour un statut `ARCHIVED` sur
  Task : masque la visibilité sans suppression physique, nettoyé plus tard par un futur
  `clean_finished_tasks`.
- Le frontend affichera un avertissement avant de procéder à une désactivation de Routine si
  les Task associées ne sont pas toutes en `PLANNED` — validation UX uniquement, pas un
  blocage côté backend.
