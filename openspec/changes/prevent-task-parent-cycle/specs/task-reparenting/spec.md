## Objet

Permet à un utilisateur de réorganiser sa hiérarchie de tâches après création en changeant le
parent d'une tâche, tout en garantissant que la structure parent/enfant ne puisse jamais contenir
de cycle.

## Exigences ajoutées

### Exigence : Le parent d'une tâche peut être changé après création
Le système DOIT permettre au propriétaire d'une tâche de changer le `parent_id` de cette tâche
vers une autre tâche, ou de l'effacer (rendant la tâche de premier niveau), après que la tâche a
déjà été créée.

#### Scénario : Déplacer une tâche sous un nouveau parent
- **QUAND** le propriétaire demande de définir le parent de la tâche A comme la tâche B, où B
  n'est actuellement ni un ancêtre ni un descendant de A
- **ALORS** le système met à jour le parent de A vers B et retourne la tâche mise à jour avec
  `parent_id` reflétant B

#### Scénario : Effacer le parent d'une tâche
- **QUAND** le propriétaire demande d'effacer le parent de la tâche A (le mettre à néant)
- **ALORS** le système met à jour A pour qu'elle n'ait plus de parent et retourne la tâche mise à
  jour avec `parent_id` égal à néant

#### Scénario : Reparenter vers le parent actuel
- **QUAND** le propriétaire demande de définir le parent de la tâche A comme le parent qu'elle a
  déjà
- **ALORS** le système accepte la requête comme un no-op et retourne la tâche inchangée

### Exigence : Le changement de parent met à jour l'horodatage de modification de la tâche
Le système DOIT mettre à jour `updated_at` de la tâche modifiée lorsque son `parent_id` change
effectivement (affectation à un nouveau parent, ou effacement), et DOIT le laisser inchangé pour
un reparentage no-op (vers le parent déjà courant). Les autres tâches consultées pendant la
validation (parent cible, ancêtres traversés) ne voient jamais leur propre `updated_at` modifié
par cette opération, puisqu'elles ne sont jamais persistées.

#### Scénario : Un reparentage effectif met à jour l'horodatage
- **QUAND** le propriétaire déplace la tâche A sous un nouveau parent B, ou efface le parent de A
- **ALORS** le système met à jour `updated_at` de A à l'heure de la requête

#### Scénario : Un reparentage no-op ne modifie pas l'horodatage
- **QUAND** le propriétaire demande de définir le parent de la tâche A comme le parent qu'elle a
  déjà
- **ALORS** le système laisse `updated_at` de A inchangé

### Exigence : Le reparentage est limité au propriétaire de la tâche
Le système DOIT uniquement permettre au propriétaire d'une tâche de changer son parent, et DOIT
uniquement accepter comme nouveau parent une tâche appartenant au même utilisateur.

#### Scénario : La tâche n'existe pas ou n'appartient pas au demandeur
- **QUAND** un utilisateur demande de changer le parent d'une tâche qui n'existe pas, ou qui
  appartient à un autre utilisateur
- **ALORS** le système rejette la requête avec une erreur de ressource non trouvée

#### Scénario : Le parent demandé n'existe pas ou n'appartient pas au demandeur
- **QUAND** un utilisateur demande de définir le parent d'une tâche comme une tâche qui n'existe
  pas, ou qui appartient à un autre utilisateur
- **ALORS** le système rejette la requête avec une erreur de ressource non trouvée

### Exigence : Le reparentage ne peut pas introduire de cycle dans la hiérarchie des tâches
Le système DOIT rejeter tout changement de parent qui rendrait une tâche son propre ancêtre,
directement ou transitivement — y compris définir une tâche comme son propre parent, ou définir
le parent d'une tâche comme l'un de ses propres descendants. Ce contrôle porte sur toute la
descendance de la tâche concernée par le changement : ni la tâche, ni aucun de ses descendants (à
quelque profondeur que ce soit), ne peut devenir le parent de cette tâche ou de l'un quelconque de
ses ancêtres.

#### Scénario : Une tâche ne peut pas devenir son propre parent
- **QUAND** le propriétaire demande de définir le parent de la tâche A comme la tâche A elle-même
- **ALORS** le système rejette la requête avec une erreur et le parent de A reste inchangé

#### Scénario : Une tâche ne peut pas être déplacée sous son propre descendant
- **QUAND** la tâche A est un ancêtre de la tâche C (directement, ou via des tâches
  intermédiaires), et que le propriétaire demande de définir le parent de A comme la tâche C
- **ALORS** le système rejette la requête avec une erreur et le parent de A reste inchangé

#### Scénario : Un descendant ne peut pas devenir le parent d'un ancêtre
- **QUAND** la tâche D est un descendant de la tâche A (directement, ou via des tâches
  intermédiaires), que la tâche X est un ancêtre de A (directement, ou via des tâches
  intermédiaires), et que le propriétaire demande de définir le parent de X comme la tâche D
- **ALORS** le système rejette la requête avec une erreur et le parent de X reste inchangé

#### Scénario : Le reparentage non lié n'est pas affecté
- **QUAND** le propriétaire demande de définir le parent de la tâche A comme la tâche B, où B
  n'est ni un ancêtre ni un descendant de A
- **ALORS** le système accepte la requête, quelle que soit la profondeur des hiérarchies propres
  de A ou de B
