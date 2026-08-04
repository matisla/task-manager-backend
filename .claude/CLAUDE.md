# CLAUDE.md

Ce fichier fournit des instructions pour Claude Code (claude.ai/code) lorsqu'il travaille sur ce dépôt.

## Langue

- Le code et commentaires devront par convention toujours être données anglais.
- Les interactions et réponses destinées à l'humain et non présent dans le dépôt, toujours en français. 
- Les noms de variables, fonctions, classes, fichiers suivent les conventions Python standard et doivent être en anglais. 
- La spec devra être en français.

# Présentation du projet

Application backend construite avec Python et FastAPI, devant suivre les standards moderne, 
afin d'apprendre à développer des projets future sur cette même base technique. 

## Objectifs

Cette application devra être robuste, maintenable et scalable, dans le but de servir de
référence et pouvoir être mise en production sans gros changement dans le code.

## Stack technique

- Langage: Python 3.14
- Framework: FastAPI
- Serveur ASGI: Uvicorn
- Gestion des dépendances: uv
- Base de données: PostreSQL avec asyncpg
- Alembic: pour les migrations
- ORM / Driver: SQLModel
- Validation: Pydantic
- Gestion des paramètres: Pydantic settings
- Linter: ruff check
- Formatter: ruff format, isort

## Structure du projet

- Pour chaque domaine fonctionnel a sont module dans `app/`.
- On utilise la séparation le domaine en sous fichier:
    - models: pour la base de données
    - repository: pour les transactions avec la base de données
    - services: contient la logique métier
    - router: le routing du domaine 
    - schemas: les schemas pour la validation de données entrantes et sortantes
- Les fichiers seront créé uniquement si necessaire (schemas.py, models.py, etc.)
- Ce qui est commun aux domaines se retrouve dans `app/core`. 
- Les settings sont géré dans `config` appartenant au domaine `core`

## Commandes Courantes

```bash
# install dependancies
uv add PACKAGE

# installer les dependances pour le développement ou les tests
uv add --dev PACKAGE

# lancer un outil
uvx <tool> ...

# lancer les tests
uv run pytest ...

# interaction avec l'application en dev, pour les logs etc.
docker compose ...

# créer une révision alembic (autogenerate) après modification d'un model
uv run alembic -m "..."
```

## Convention de code

- Typage explicite obligatoire (type hints python) sur toutes les functions publiques.
- Utiliser les modèles Pydantic pour valider les entrées et sorties des endpoints.
- Docstrings en anglais et obligatoire pour les classes et fonctions au format Google Style.
- Mettre à jour la Docstrings, si et seulement si la logique change.
- Les erreurs métier doivent être gérées via des exceptions FastAPI (`HTTPException`) ou des gestionnaires d'exceptions dédiés.

## Tests

### Stack technique

- Framework: pytest
- Données factice: Faker, factory_boy
- Requetes: httpx

## Migrations (Alembic)

- Dès qu'un `models.py` (`app/<feature>/models.py`) est créé ou modifié (nouveau champ, nouvelle table, relation, contrainte, etc.),
  la création d'une nouvelle révision Alembic doit être être proposé à l'utilsateur dans la même tâche, si accepté créer via `uv run alembic revision --autogenerate -m "message"`.
- Le message de révision doit être en anglais et décrire le changement de schéma (ex: `"add due_date to task"`).
- Toujours relire le fichier généré dans `alembic/versions/` avant de le considérer terminé : l'autogenerate peut manquer certains changements (renommage de colonne, changement de type sur SQLite, etc.) ou nécessiter un ajustement manuel.
- Ne pas exécuter `alembic upgrade head` sur l'environnement de dev sans le demander à l'utilisateur au préalable (action ayant un effet sur une base partagée).
- `alembic/env.py` construit dynamiquement l'URL de connexion à partir des settings de l'application (`get_settings().db.connexion_url`) : ne pas coder en dur une URL dans `alembic.ini`.

## Notes pour Claude

- Toujours répondre et expliquer en **français**, même si le code produit est en anglais.
- Avant de modifier un fichier existant, vérifier les conventions déjà en place dans le dépôt plutôt que d'imposer un nouveau style.
- Ne pas ajouter de dépendances sans les mentionner explicitement dans les explications.
- Après toute modification d'un `models.py`, créer proposer à l'utilisateur de créer la révision Alembic correspondante (voir section "Migrations (Alembic)"), sans attendre une demande explicite.
