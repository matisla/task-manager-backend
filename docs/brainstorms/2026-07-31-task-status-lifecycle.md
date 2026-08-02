# Brainstorm : Statuts de Task (cycle de vie et transitions)

## Contexte

Extrait de [`2026-07-31-routine-recurring-tasks.md`](2026-07-31-routine-recurring-tasks.md) :
le statut `Task.status` y est évoqué à plusieurs reprises (transitions implicites, statuts
`CANCELLED`/`ARCHIVED` envisagés) sans jamais faire l'objet d'un graphe de transitions complet,
contrairement à `Routine.status` qui y est intégralement défini (cf. Q8 de ce brainstorm). Ce
nouveau brainstorm reprend ce qui concerne spécifiquement `Task.status` et sert de point de
départ pour trancher ce qui reste ouvert.

## Décisions

### Nature des transitions (explicite vs implicite)

Comme pour `Routine.status`, les changements de `Task.status` sont le plus souvent **explicites**
(action utilisateur dédiée), mais peuvent aussi être déclenchés **implicitement**, en effet de
bord d'une autre action métier. Chaque transition (explicite ou implicite) doit être validée
côté service (logique dans `services.py`, pas dans le routeur) : si les conditions du statut
cible ne sont pas remplies, une `HTTPException` explicite est levée plutôt que d'accepter
silencieusement le changement.

### Pattern d'API pour les transitions explicites

`POST /tasks/{id}/{status}` — même principe que pour `Routine` (`POST /routines/{id}/{status}`),
retenu plutôt qu'un `PATCH` générique sur le champ `status`.

### Terminologie : « Task ouverte » vs « Task active »

Préférer « Task ouverte » pour désigner une Task non terminée, afin d'éviter la confusion avec
le statut `ACTIVE` de `Routine` — qui ne s'applique pas à `Task`. **Mise à jour** : maintenant
que `CANCELLED`/`ARCHIVED` existent, « Task ouverte » se définit comme
`status not in (DONE, CANCELLED, ARCHIVED)`, et non plus seulement `status != DONE` (impact sur
la requête `routine_id` + filtre de statut décrite dans le brainstorm routines, à corriger là-bas
également).

### Nouveaux statuts `CANCELLED` et `ARCHIVED`

Ajout à l'enum `Status` de `Task` :
- `CANCELLED` : tâche abandonnée (échec / décision de ne pas la réaliser).
- `ARCHIVED` : tâche masquée du frontend sans suppression physique en base (permet de conserver
  l'historique, utile notamment pour le critère d'identité côté `Routine`).

### Graphe des transitions (`Task.status`)

```
BACKLOG ⇄ PLANNED               (programmation / déprogrammation, mode passif)
PLANNED → IN_PROGRESS           (démarrage du travail, mode actif)
IN_PROGRESS ⇄ PAUSED            (mise en pause / reprise du travail)
IN_PROGRESS ⇄ WAITING           (attente d'un élément externe, suivi actif malgré le blocage)
PAUSED ⇄ WAITING                (bascule entre les deux formes d'attente)
IN_PROGRESS → DONE              (succès : uniquement après un passage actif par IN_PROGRESS)
{BACKLOG, PLANNED, IN_PROGRESS,
 PAUSED, WAITING} → CANCELLED   (échec/abandon : possible depuis n'importe quel statut non
                                  terminal, contrairement à DONE)
{DONE, CANCELLED} → ARCHIVED    (masquage sans suppression physique)
ARCHIVED : terminal, aucune transition sortante
```

### Suppression logique via `DELETE /tasks/{id}`

Règle à trois branches :
- `status == BACKLOG` : suppression **physique** réelle (aucune progression réelle à préserver —
  jamais passée par un statut actif, pas d'historique utile).
- `status ∈ {DONE, CANCELLED}` : `DELETE` déclenche la transition implicite vers `ARCHIVED` (pas
  de suppression physique, historique conservé).
- tout autre statut (`PLANNED`, `IN_PROGRESS`, `PAUSED`, `WAITING`) : `DELETE` retourne une
  erreur explicite — il faut d'abord annuler (`CANCELLED`) ou terminer (`DONE`) la tâche.

### Effets de bord des transitions sur `completed_at` et `updated_at`

- `completed_at` : fixé automatiquement à `now(UTC)` lors de la transition `IN_PROGRESS → DONE`
  (champ existant dans le modèle, jusqu'ici jamais renseigné).
- `updated_at` : **non modifié** par les transitions de statut explicites (`POST
  /tasks/{id}/{status}`) ni implicites. Ce champ reste réservé au marqueur « détaché » posé par
  l'édition de contenu (titre, description, dates — non encore implémentée) : une Task générée
  par une Routine qui progresse normalement dans son cycle de vie ne doit pas devenir
  « détachée » du seul fait d'avancer, sous peine de rendre inopérant le mécanisme de delta décrit
  ci-dessous.

### Critère d'identité Task existante / Task candidate (calcul de delta côté Routine)

Critère retenu : clé naturelle `(routine_id, due_date)`. Deux Task sont la même occurrence si
même Routine et même `due_date`.

Mécanisme de delta (réactivation `Routine.INACTIVE → ACTIVE`, modification de RRULE) :
- Une Task existante dont la `due_date` correspond à une entrée de la liste cible (nouvelle
  RRULE ou recalcul) est **conservée telle quelle**, pas recréée.
- Une entrée de la liste cible sans Task existante correspondante déclenche la **création**
  d'une nouvelle Task.
- Une Task existante dont la `due_date` ne correspond plus à aucune entrée de la liste cible
  passe automatiquement en statut `CANCELLED` (plutôt que d'être supprimée ou laissée à
  s'accumuler en doublon avec les nouvelles occurrences).
- **Exception** : une Task « détachée » (modifiée manuellement par l'utilisateur, `updated_at`
  non nul) est **préservée** même si sa `due_date` ne correspond plus à la liste cible — elle
  n'est jamais annulée automatiquement. Seul l'utilisateur peut statuer explicitement sur son
  sort (cohérent avec la protection déjà actée dans le brainstorm routines pour la modification
  de RRULE).

## En cours

*(vide)*

## Information complémentaire

- `Task.routine_id: uuid.UUID | None` (FK vers `Routine`, distincte de `parent_id` réservé aux
  sous-tâches) permet de retrouver la Task ouverte d'une Routine via `routine_id` +
  `status not in (DONE, CANCELLED, ARCHIVED)` (mis à jour, cf. "Terminologie « Task ouverte »").
- Une Task « détachée » (modifiée manuellement par l'utilisateur, `updated_at` non nul) est
  protégée de la suppression/recréation automatique lors d'une modification de RRULE — ce
  marqueur pourrait aussi jouer un rôle dans les futures règles de transition de statut.
- Pour rappel, le graphe de `Routine.status` (déjà tranché) est :
  `UNDEFINED → ACTIVE → {INACTIVE, ARCHIVED}`, `INACTIVE → {ACTIVE, ARCHIVED}`, `ARCHIVED`
  terminal — certaines transitions de `Routine` dépendent de l'état des Task liées (ex:
  `ACTIVE → ARCHIVED` exige que toutes les Task liées soient `DONE` ou supprimées), donc le
  graphe de `Task.status` à définir ici n'est pas indépendant de celui de `Routine`.

## Notes

- Idée soulevée en aparté (brainstorm routines) : `Task.CANCELLED` serait utile à la fois pour
  `Routine.ACTIVE → INACTIVE` et pour le critère d'identité en calcul de delta. Idée similaire
  évoquée pour `Task.ARCHIVED`.
- Spec issue de ce brainstorm : [`docs/specs/01-task-status-lifecycle.md`](../specs/01-task-status-lifecycle.md).
  Point non explicitement tranché ici mais résolu dans la spec (section "Cas limites") : un
  `DELETE /tasks/{id}` sur une Task déjà `ARCHIVED` est traité comme idempotent (`204` sans
  effet), ce cas n'étant pas couvert par la règle à trois branches définie plus haut. À tester
  explicitement lors de l'implémentation.

# Q&A log

## Q1 - Graphe complet des transitions de `Task.status`

**Question** : quel est le graphe complet des transitions autorisées pour `Task.status`,
incluant les 6 statuts existants (`BACKLOG`, `PAUSED`, `WAITING`, `PLANNED`, `IN_PROGRESS`,
`DONE`) et les statuts `CANCELLED`/`ARCHIVED` envisagés dans le brainstorm routines ?

**Réponse** : graphe validé (cf. Décisions, section "Graphe des transitions"). Points clés :
- Flux nominal : `BACKLOG → PLANNED → IN_PROGRESS → DONE`, avec retour possible
  `PLANNED → BACKLOG` si la tâche n'est finalement pas assez cadrée.
- `PAUSED` et `WAITING` sont deux formes d'attente accessibles depuis `IN_PROGRESS` et
  interchangeables entre elles (`PAUSED ⇄ WAITING`), toutes deux avec retour vers
  `IN_PROGRESS`.
- `DONE` ne se constate qu'après un passage actif par `IN_PROGRESS` (succès).
- `CANCELLED` (échec/abandon) est accessible depuis n'importe quel statut non terminal
  (`BACKLOG`, `PLANNED`, `IN_PROGRESS`, `PAUSED`, `WAITING`), contrairement à `DONE`.
- `ARCHIVED` (masquage sans suppression physique) n'est accessible que depuis `DONE` ou
  `CANCELLED`, et est terminal.
- `DELETE /tasks/{id}` : erreur si le statut n'est ni `DONE` ni `CANCELLED` ; sinon déclenche
  la transition implicite vers `ARCHIVED`. Exception `BACKLOG` proposée mais pas encore
  confirmée (cf. "En cours").

## Q2 - Exception `BACKLOG` pour `DELETE /tasks/{id}`

**Question** : la règle générale `DELETE` (erreur sauf `DONE`/`CANCELLED` → `ARCHIVED`)
doit-elle s'appliquer telle quelle à une Task `BACKLOG`, ou une tâche jamais entrée en phase
active mérite-t-elle une suppression physique directe plutôt qu'un passage obligé par
`CANCELLED` ?

**Réponse** : `BACKLOG` est exempté — `DELETE` sur une Task `BACKLOG` effectue une suppression
physique réelle, sans passer par `CANCELLED`/`ARCHIVED`. Raison : aucune progression réelle
n'existe encore pour ce statut, donc rien d'utile à préserver en base.

## Q3 - Critère d'identité Task existante / candidate et mécanisme de delta

**Question** : le critère d'identité `(routine_id, due_date)` (proposé en Q10 du brainstorm
routines) est-il confirmé maintenant que `Task.CANCELLED` existe ? Et comment se comporte
précisément le calcul de delta quand un changement de RRULE décale les dates (ex: 5 anciennes
occurrences vs 5 nouvelles, non alignées) ?

**Réponse** : critère `(routine_id, due_date)` confirmé. Mécanisme de delta précisé : les Task
existantes dont la `due_date` ne correspond à aucune entrée de la nouvelle liste cible passent
automatiquement en `CANCELLED` (au lieu d'être supprimées ou de s'accumuler en doublon avec les
nouvelles occurrences) — sauf si la Task est « détachée » (`updated_at` non nul), auquel cas
elle est préservée telle quelle : seul l'utilisateur peut statuer explicitement sur son sort.

## Q4 - `completed_at` doit-il être renseigné automatiquement ?

**Question** : le champ `Task.completed_at` existe dans le modèle mais n'est jamais renseigné.
La transition `IN_PROGRESS → DONE` doit-elle le fixer automatiquement ?

**Réponse** : oui — `TaskService` fixe `completed_at = now(UTC)` lors de cette transition.

## Q5 - Les transitions de statut doivent-elles « détacher » la Task (`updated_at`) ?

**Question** : le marqueur « détaché » (`updated_at` non nul, cf. Information complémentaire)
doit-il aussi être posé par les transitions explicites de statut, ou reste-t-il réservé à
l'édition de contenu ?

**Réponse** : réservé à l'édition de contenu. Les transitions de statut (explicites ou
implicites) ne modifient jamais `updated_at` — une Task générée par une Routine qui progresse
normalement dans son cycle de vie ne doit pas devenir « détachée » du seul fait d'avancer.
