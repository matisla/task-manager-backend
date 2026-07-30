
# CLAUDE.md

Ce fichier fournit des instructions pour Claude Code (claude.ai/code) lorsqu'il travaille sur ce dépôt.

## Langue

- Le code et commentaires devront par convention toujours être données anglais.
- Les interactions et réponses destinées à l'humain et non présent dans le dépôt, toujours en français. 
- Les noms de variables, fonctions, classes, fichiers suivent les conventions Python standard et doivent être en anglais. 

# Présentation du projet

Application backend construite avec Python et FastAPI, devant suivre les standards moderne, 
afin d'apprendre à développer des projets future sur cette même base technique. 

## Stack technique

- Langage: Python 3.14
- Framework: FastAPI
- Serveur ASGI: Uvicorn
- Gestion des dépendances: uv
- Base de données: SQLite pour les tests, PostreSQL pour l'environement de dev et en production.
- Alembic: pour les migrations
- ORM / Driver: SQLModel
- Validation: Pydantic
- Gestion des paramètres: Pydantic settings
- Linter: ruff
- Formatter: black, isort

## Structure du projet

- Pour chaque domaine fonctionnel on crée un dossier dans `app/` (placeholder: <feature>).
- Les fichiers seront créé uniquement si necessaire (schemas.py, models.py, etc.)
- Il existe en supplément les dossiers `config` pour la configuration.

```
app/
|---- <feature>          # separation for entities: auth, tasks, etc. 
      |---- __init__.py
      |---- schemas.py
      |---- models.py
      |---- router.py
      |---- services.py
      |---- ...
|---- config # 
      |---- __init__.py
      |---- core.py      # main Settings class
      |---- logging.py   # schemas and config for logging
      |---- database.py  # schemas and config for database 
      |---- ...
|---- __init__.py
|---- database.py   # generator for session and engine
|---- main.py       # app builder
|---- asgi.py       # entrypoint for uvicorn
tests/
|---- <feature>     # contains tests for app/<feature>
|---- ...           # contains conftest.py and more

scripts/            # contains scripts if needed
Dockerfile          # used to build app into container
docker-compose.yaml # docker environment to start app in dev mode
pyproject.yaml      # project file used via uv
logging.yaml        # logging configuration for logging module
.env                # env configuration for app container used in development (not commited)
```

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
- Un routeur FastAPI (APIRouter) par domaine functionnel, monté dans `create_app` présent dans `main.py`.
- Docstrings en anglais et obligatoire pour les classes et fonctions au format Google Style.
- Les erreurs métier doivent être gérées via des exceptions FastAPI (`HTTPException`) ou des gestionnaires d'exceptions dédiés.

## Tests

### Stack technique

- Framework: pytest
- Données factice: Faker 
- Requetes: httpx

### Autres consignes

- Base de données tests/database.db, à supprimer si nécessaire AVANT les tests

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
