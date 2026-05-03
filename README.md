Système MLOps de veille économique automatisée : un moteur DL (Transformers) analyse le sentiment des articles NYT, ses sorties alimentent un modèle de tendance (Prophet), l'ensemble est géré via un pipeline CI/CD (Jenkins) avec retraining automatisé, versioning (MLflow) et monitoring (Evidently).


---
## Install

'''
    $ pyenv local 3.12.9
    $ python3 -m venv .venv-nyt
    $ source .venv-nyt/bin/activate
    $ pip install --upgrade pip
'''

### Jenkins

### PostgreSQL
créer un projet dans Neon
créér une database dans l'interface

### pipeline
rendre pipeline importable comme module

creation pyproject.toml à la racine
$ pip install -e .


---
## Diagramme de contexte
![C4 Niveau 1 — Contexte](docs/diagrams/nyt_c4_c1.svg)

---
## Diagramme de conteneur
![C4 Niveau 2 — Conteneurs](docs/diagrams/nyt_c4_c2.svg)