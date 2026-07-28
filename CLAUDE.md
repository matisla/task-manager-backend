
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
- ORM / Driver: SQLModel
- Validation: Pydantic
- Gestion des paramètres: Pydantic settings
- Linter: ruff
- Formatter: black, isort

## Structure du projet

```
app/
|---- <feature>          # separation for entities: auth, tasks, etc. 
      |---- __init__.py
      |---- schemas.py
      |---- models.py
      |---- router.py
      |---- service.py
|---- config # 
      |---- __init__.py
      |---- core.py      # main Settings class
      |---- logging.py   # schemas and config for logging
      |---- database.py  # schemas and config for database 
|---- __init__.py
|---- database.py   # generator for session and engine
|---- main.py       # app builder
|---- asgi.py       # entrypoint for uvicorn
|---- logging.yaml  # logging configuration for logging module
tests/
|---- <feature>     # contains tests for app/<feature>
scripts/            # contains scripts if needed
Dockerfile          # used to build app into container
docker-compose.yaml # docker environment to start app in dev mode
pyproject.yaml      # project file used via uv
```

## Commandes Courantes

```bash
# install dependancies
uv add PACKAGE

# instaler les dependances pour le développement ou les tests
uv add --dev PACKAGE

# lancer les tests
uvx pytest ...

# interaction avec l'application en dev, pour les logs etc.
docker compose ...
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

## Notes pour Claude

- Toujours répondre et expliquer en **français**, même si le code produit est en anglais.
- Avant de modifier un fichier existant, vérifier les conventions déjà en place dans le dépôt plutôt que d'imposer un nouveau style.
- Ne pas ajouter de dépendances sans les mentionner explicitement dans les explications.
