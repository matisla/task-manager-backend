# Idées


## Gestion des permissions et attribution

Problématique: Qui a le contrôle sur quoi ?

Opération:

- Création d'objets
- Suppression d'objets
- Modifications d'objets
- Les changements de status des objets

- Assigner une tâche (celui qui fait, une ou plusieurs personnes)
- Observer une tâche (celui qui doit être mis au courant, une ou plusieurs personnes)

## Gestion des Groupes

- Groupes de tâches
- Groupes d'utilisateurs
- Permissions selon groupes (individuelle > groupes)

ex:
- User_A créer la routine "ménage" et l'assigne à B.
- User_B, voie la tâche de la routine et la ferme.
- A peux suivre les tâches de B, et vice versa (car tout deux font partie de "ménage".
- B peux fermé la tâche ménage, mais pas A, car assigné à B.

## SQL injection projection

- A tester avec les filters
- A tester avec les create, delete, etc.

## protection contre les boucles infini parent-enfant.

- lors de la création d'une tâche ou de l'attribution d'un parent à une tâche.
- vérifier les parents:
  - aucun des enfants ou la tâche elle même, ne doit être un des parents des ancêtres de la tâche.
  - la tâche elle même ne peut être sont propre parent.

- A -> B -> C, si je crée D, enfant de C, ni C, ni B, ni A, ni D, ne peux avoir D pour parent.


