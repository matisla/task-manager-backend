# Critique : Spec 01 — Cycle de vie du statut des Task

**Spec évaluée** : [`01-task-status-lifecycle.md`](01-task-status-lifecycle.md) (statut au moment
de la critique : *Prête pour implémentation*)
**Brainstorm source** : [`../brainstorms/2026-07-31-task-status-lifecycle.md`](../brainstorms/2026-07-31-task-status-lifecycle.md)
**Date** : 2026-08-01
**Méthode** : relecture de la spec et du brainstorm, confrontés au code réel
(`app/tasks/models.py`, `router.py`, `schemas.py`, `services.py`, `app/database.py`,
`tests/conftest.py`, `tests/auth/factories.py`) plutôt qu'à leur seule description.

## Synthèse

La spec est solide sur son cœur de sujet (graphe de transitions, règle de suppression à trois
branches, sécurité d'accès) et correctement ancrée dans le code existant. Trois angles morts
sont cependant assez sérieux pour justifier une correction de la spec **avant** de lancer
`implement-spec` — ils ne sont pas de simples détails d'implémentation :

1. La hiérarchie parent/enfant (`Task.parent_id`) n'est mentionnée nulle part, ni dans le
   brainstorm ni dans la spec, alors qu'elle interagit directement avec les transitions et la
   suppression physique.
2. `ARCHIVED` — défini par le brainstorm lui-même comme « masquée du frontend » — n'est filtré
   nulle part dans `GET /tasks`. La spec introduit le statut sans jamais toucher à l'endpoint de
   listing, ce qui contredit sa propre définition dès la première implémentation.
3. Le plan de tests suppose qu'on peut « créer un deuxième utilisateur/token dans le test »
   pour valider l'autorisation, mais l'infrastructure de test actuelle (`client` fixture) rend
   cela structurellement impossible tel quel.

Le reste (7 constats) est correctif ou consultatif : à corriger pendant l'implémentation, ou à
confirmer explicitement avec vous, sans remettre en cause l'architecture proposée.

## Constats bloquants — à trancher avant `implement-spec`

### 1. Hiérarchie parent/enfant totalement absente de la réflexion

`Task.parent_id` (FK vers `task.id`, sans `ondelete` explicite) permet des sous-tâches, mais ni
le brainstorm ni la spec n'abordent :

- **Cohérence de statut** : rien n'empêche de passer un parent à `DONE` pendant que ses enfants
  sont encore `IN_PROGRESS`, ni de `CANCELLED`/`ARCHIVED` un parent dont les enfants sont actifs.
  Est-ce voulu (statuts totalement indépendants), ou faut-il une règle de propagation /
  interdiction (« un parent ne peut passer `DONE` que si tous ses enfants le sont ») ?
- **Suppression physique d'un `BACKLOG` avec enfants** : `TaskService.delete` fait un
  `session.delete()` réel pour `BACKLOG`. Si cette tâche a des enfants (`children`), il faut
  décider explicitement : suppression en cascade des enfants, refus (`409`) si des enfants
  existent, ou détachement (`parent_id = None`) ? La spec ne dit rien, et le comportement par
  défaut diffère silencieusement selon l'environnement (voir constat n°6).

Ce point doit être tranché car il modifie potentiellement le graphe de transitions et la
méthode `delete` elle-même — pas une simple note en marge.

### 2. `ARCHIVED` n'est filtré nulle part dans `list_tasks`

Le brainstorm définit `ARCHIVED` comme « tâche **masquée du frontend** sans suppression
physique ». Or `GET /tasks` (`app/tasks/router.py:31`) fait toujours
`select(Task).where(Task.user_id == user.id)`, sans filtre de statut, et la spec ne touche pas
à cet endpoint (absent du §4 « Router »). Résultat concret : dès qu'un `DELETE` transforme une
Task `DONE`/`CANCELLED` en `ARCHIVED` (ou qu'une transition explicite y mène), elle continue
d'apparaître dans la liste par défaut — en contradiction directe avec la définition même du
statut que la spec introduit.

Non traité non plus en "Non-objectifs" : ce n'est donc pas une exclusion volontaire, mais un
oubli. À trancher : filtre par défaut (`status != ARCHIVED` sauf `?include_archived=true`), ou
report explicite vers une future spec de listing/filtrage — mais dans ce dernier cas il faut le
dire noir sur blanc, car en l'état la spec laisse un comportement incohérent avec son propre
vocabulaire.

### 3. Le plan de tests suppose une capacité que la fixture actuelle n'a pas

`tests/conftest.py` :

```python
@cache
def override_get_current_user() -> User:
    """Same fake user across requests, so ownership (eg. user_id) stays consistent."""
    return UserFactory.build()
```

`override_get_current_user` est décoré `@cache` **sans argument** : un seul et même `User` est
mémorisé pour toute la session pytest, et `client`/`current_user` sont eux-mêmes
`scope="session"`. La fixture `client` ne peut donc *structurellement* pas représenter deux
utilisateurs différents — quel que soit le token envoyé, le `Depends(get_current_user)` est
outrepassé et renvoie toujours le même utilisateur mémorisé.

La spec (Plan de tests, « Autorisation ») dit qu'il suffit de « créer un deuxième
utilisateur/token dans le test » — c'est trompeur : avec `client`, c'est impossible sans
modifier l'override en cours de test. Deux vraies options existent :
- utiliser `auth_client` (flux JWT réel : `/auth/register` + `/auth/login` pour deux comptes,
  puis header `Authorization` manuel sur chaque requête) — change complètement le style des
  tests d'autorisation par rapport au reste de `test_task.py` ;
- ou modifier ponctuellement `app.dependency_overrides[get_current_user]` dans le test concerné
  puis le restaurer — fragile avec des fixtures `scope="session"` partagées entre tests.

Ce point doit être clarifié avant l'implémentation des tests d'autorisation, sans quoi le
critère d'acceptation correspondant (« retournent 404 ») risque d'être soit non testé, soit
testé au prix d'un hack qui complique la suite de tests pour tout le monde.

## Constats majeurs — correctifs à appliquer pendant l'implémentation

### 4. `transition_task` : l'appel à `get_owned_or_404` n'est pas explicite dans la spec

Le §3 introduit `get_owned_or_404` en le justifiant essentiellement par le nouvel endpoint de
transition (« comme les nouveaux endpoints de transition opèrent sur une Task précise, cette
vérification devient indispensable »), mais le §4 ne mentionne **que** `detail_task` et
`delete_task` comme l'utilisant, et le corps de `transition_task` dans l'exemple de code est un
simple `...`. Un implémenteur pressé pourrait très bien coder `transition_task` avec un
`session.get(Task, task_id)` brut (comme l'existant), recréant exactement la faille
d'autorisation que la spec cherche à corriger — sur l'endpoint le plus sensible (celui qui fait
changer d'état une ressource). À corriger dans la spec : dire explicitement que les **trois**
endpoints (`detail_task`, `delete_task`, `transition_task`) passent par `get_owned_or_404`.

### 5. Piège du schéma SQLite figé (`tests/database.db`)

`get_engine()` (`app/database.py:12-41`) est `@cache` et fait
`SQLModel.metadata.create_all(engine, checkfirst=True)` — `checkfirst=True` signifie qu'une
table déjà existante n'est **pas** modifiée. Sous SQLite, l'`Enum` de `Status` est émulé par un
`CHECK` constraint généré à partir des membres connus au moment de la création de la table. Si
`tests/database.db` existe déjà (créé avant l'ajout de `CANCELLED`/`ARCHIVED`), toute tentative
d'insérer une Task avec l'un de ces deux nouveaux statuts violera l'ancien `CHECK` constraint et
échouera avec une erreur SQL peu explicite — pas un `409` métier, une vraie erreur d'intégrité.

Le `CLAUDE.md` du projet mentionne déjà la nécessité de supprimer `tests/database.db` avant les
tests, mais de façon générique. Ici c'est un piège quasi garanti si l'étape est oubliée
spécifiquement pour cette tâche — à rappeler explicitement dans le plan d'implémentation de la
spec (étape 6), pas seulement dans les conventions générales du projet.

### 6. Asymétrie SQLite / PostgreSQL sur la contrainte FK `parent_id`

Aucun `PRAGMA foreign_keys=ON` n'est activé pour SQLite (vérifié : aucun `event.listens_for` ni
pragma dans `app/database.py`). Conséquence directe du constat n°1 : supprimer physiquement une
Task `BACKLOG` ayant des enfants...
- ... sous **SQLite** (tests) : réussit silencieusement, laisse des `Task.parent_id` orphelins
  pointant vers un id qui n'existe plus (corruption silencieuse des données de test) ;
- ... sous **PostgreSQL** (dev/prod) : lève une violation de contrainte FK (erreur 500 brute,
  non gérée par `TaskService.delete`, qui ne l'anticipe pas).

Deux environnements, deux comportements radicalement différents pour le même appel — un bug qui
ne peut être détecté qu'en environnement PostgreSQL, jamais en test. À corriger conjointement
avec le constat n°1 (politique explicite vis-à-vis des enfants avant suppression physique).

### 7. `downgrade()` Alembic non mentionné pour l'ajout de valeurs à un ENUM PostgreSQL

Le §6 de la spec couvre bien l'`upgrade()` (autogenerate insuffisant, `ALTER TYPE ... ADD
VALUE`, bloc autocommit), mais ne dit rien du `downgrade()`. PostgreSQL ne permet pas de retirer
une valeur d'un `ENUM` par un simple `ALTER TYPE ... DROP VALUE` (cette commande n'existe pas) :
un vrai retour arrière nécessite de recréer entièrement le type (nouveau type sans les valeurs
ajoutées, migration des colonnes, suppression de l'ancien type) — un downgrade correct serait
donc coûteux, voire irréaliste si des lignes existantes utilisent déjà `CANCELLED`/`ARCHIVED` au
moment du rollback. À noter explicitement dans la spec, au moins comme limitation connue
(`downgrade()` marqué `NotImplementedError` ou commentaire explicite plutôt que silence).

## Points à confirmer — le design est déjà tranché, mais mérite d'être challengé

### 8. `CANCELLED` et `DONE` sont des culs-de-sac : pas de réouverture possible

Le graphe validé (brainstorm Q1) ne permet aucun retour de `CANCELLED` ou `DONE` vers un statut
actif — seule sortie : `ARCHIVED`, terminal. Concrètement : une tâche annulée par erreur, ou
marquée terminée trop tôt, ne peut **jamais** être rouverte ; il faut recréer une nouvelle Task
de toutes pièces (perdant `created_at` d'origine, l'historique de commentaires éventuels, etc.).
C'est une décision déjà actée, donc pas un « oubli », mais aucune des deux itérations
(brainstorm ou spec) n'en discute la conséquence UX ni n'explique le choix. Vaut la peine d'une
confirmation explicite avant implémentation, tant le coût d'un retour arrière ultérieur
(rouvrir cette décision après coup) serait élevé — cela touche le graphe central de la feature.

### 9. Aucun verrouillage optimiste sur les transitions

`Task` n'a pas de colonne de version, et `TaskService.transition`/`delete` lisent puis écrivent
sans protection contre une écriture concurrente. Deux requêtes quasi simultanées sur la même
Task (ex. `IN_PROGRESS → DONE` et `IN_PROGRESS → CANCELLED` envoyées à quelques millisecondes
d'écart, cas plausible avec un double-clic ou un client qui retente une requête en timeout)
peuvent toutes deux passer la validation (lue avec le même état source) puis committer l'une
après l'autre : la seconde écrase silencieusement la première, sans erreur, sans qu'aucune des
deux requêtes ne le sache. Risque faible vu l'échelle du projet (usage personnel), mais à noter
comme limitation assumée plutôt que non-dite.

### 10. Idempotence UX du `409` sur transition vers le statut courant

La règle « `X → X` toujours rejetée (`409`) » (Cas limites) est cohérente avec l'absence de
boucle dans le graphe, mais côté UX cela signifie qu'un double-clic sur « Marquer terminé »
depuis un frontend (deux requêtes `IN_PROGRESS → DONE` par accident) renverra une erreur sur la
seconde, alors qu'un comportement idempotent (200, no-op) serait plus confortable pour
l'appelant. Décision déjà justifiable techniquement (cohérence avec le graphe), simplement à
confirmer que c'est le compromis voulu plutôt qu'un effet de bord non anticipé.

## Suggestions — non bloquantes

### 11. Enrichir le corps d'erreur du `409`

Actuellement la spec précise seulement le code `409`, pas le contenu du `detail`. Inclure le
statut courant et la liste des cibles valides (`ALLOWED_TRANSITIONS[task.status]`) dans le
message rendrait l'API nettement plus exploitable côté frontend, sans coût de conception
supplémentaire (l'information est déjà disponible dans `TaskService.transition`).

### 12. `started_at` distinct de `start_date`

`start_date` est un champ de planification (date cible, saisie à la création). Rien ne capture
le moment réel du premier passage en `IN_PROGRESS` (symétrique à `completed_at` pour `DONE`).
Pas nécessaire pour cette spec, mais cohérent avec la logique déjà actée pour `completed_at` —
à considérer pour une future itération si un suivi de durée réelle est souhaité.

### 13. Filtrage par statut sur `GET /tasks` au-delà du seul cas `ARCHIVED`

Une fois `CANCELLED`/`ARCHIVED` en place, un query param `status` (ou `open_only`) sur le
listing deviendrait probablement nécessaire assez vite pour un usage réel (retrouver l'historique
sans être noyé par les tâches terminées/annulées). Lié au constat n°2 mais plus large — à
traiter dans une spec de listing/filtrage dédiée plutôt qu'ici.

### 14. Détail d'implémentation mineur

`app/tasks/schemas.py` n'importe actuellement rien depuis `.models` ; l'ajout de
`status: Status` à `TaskRead` nécessite `from .models import Status`. Trivial, mais autant le
noter pour que `implement-spec` ne s'arrête pas dessus.

## Étapes suivantes recommandées

1. Trancher les 3 constats bloquants (idéalement via un aller-retour rapide, pas forcément une
   nouvelle session `grill-me` complète) :
   - politique parent/enfant pour les transitions et la suppression (constat 1) ;
   - filtrage (ou non, mais alors dit explicitement) d'`ARCHIVED` dans `GET /tasks` (constat 2) ;
   - stratégie de test pour l'autorisation inter-utilisateurs (constat 3).
2. Mettre à jour `01-task-status-lifecycle.md` en conséquence (Design détaillé, Cas limites,
   Plan de tests, et Non-objectifs si le filtrage de listing est explicitement repoussé).
3. Corriger les 4 constats majeurs directement dans la spec (mentions explicites suffisent pour
   3, 4, 5 ; le 4 nécessite aussi de corriger l'exemple de code du §4 pour montrer l'appel à
   `get_owned_or_404` dans `transition_task`).
4. Statuer sur les points de confirmation (8, 9, 10) — accord verbal suffisant, pas besoin de
   réouvrir le brainstorm si la réponse est « oui, c'est voulu ».
5. Une fois ce qui précède fait, relancer `implement-spec` sur la spec mise à jour.
