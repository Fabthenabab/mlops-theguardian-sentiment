Système MLOps de veille économique automatisée : un moteur DL (Transformers) analyse le sentiment des articles The Guardian, ses sorties alimentent un modèle de tendance (Prophet), l'ensemble est géré via un pipeline CI/CD (Jenkins) avec retraining automatisé, versioning (MLflow) et monitoring (Evidently).


---
## Install

'''
    $ pyenv local 3.12.9
    $ python3 -m venv .venv-theguardian
    $ source .venv-theguardian/bin/activate
    $ pip install --upgrade pip
    $ pip install -r requirements.txt
    $ pip install torch --index-url https://download.pytorch.org/whl/cpu
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
![C4 Niveau 1 — Contexte](docs/diagrams/the_guardian_c4_c1.svg)

---
## Diagramme de conteneur
![C4 Niveau 2 — Conteneurs](docs/diagrams/the_guardian_c4_c2.svg)