# ADR-000 — Gestion d'environnement : pyenv + venv + Python 3.12

Contexte :
  Le projet fraud-detection a rencontré des incompatibilités entre la version Python d'entraînement et celle d'Airflow, causant des problèmes de sérialisation et de comportement des dépendances (numpy, pandas).

Décision : pyenv pour fixer la version + venv pour isoler les dépendances
  - .python-version à la racine fixe la version pour tout le projet
  - venv créé dans cette version garantit la cohérence locale
La doc d'Airflow pour docker recommande python 3.12
  - Dockerfile HF Space : FROM python:3.12-slim

Règle projet : une seule version Python pour tous les composants.
  Tout changement de version est une décision explicite qui impacte Dockerfile, image Airflow et .python-version simultanément.

---
# ADR-001 — CI/CD : Jenkins plutôt que GitHub Actions
Date : 2026-05-01  
Contexte :
  Le projet nécessite un pipeline CI/CD pour automatiser   tests, build image et déploiement.
  Deux options principales : Jenkins (déjà en place) ou GitHub Actions.

Problème GitHub Actions :
  Runners hébergés chez GitHub — pas de contrôle sur l'environnement.
  Les secrets MLflow/AWS/Neon transitent par l'infrastructure GitHub.
  Dépendance à un service tiers pour le cœur du pipeline.

Décision : Jenkins auto-hébergé (DinD, port 8080)
  - Infrastructure déjà validée sur le projet fraud-detection
  - Contrôle total sur l'environnement d'exécution
  - Secrets gérés localement via Jenkins Credentials Store
  - Pas de coût de runner pour les jobs longs (build image Transformers)
  - Pattern Jenkinsfile déjà maîtrisé

Limite assumée :
  Jenkins nécessite une machine hôte active (run en local)
  Ce choix est justifié par la continuité avec l'infra existante et les exigences de contrôle sur les credentials.

---
# ADR-002 — Réutilisation de l'instance MLflow, isolation par Projet PostgreSQL
Date : 2026-05-01
Contexte :
  Le projet fraud-detection utilise déjà une instance MLflow sur HF Spaces avec backend Neon ostgreSQL et artifact store S3.
  Le projet NYT Sentiment nécessite le même type d'infrastructure.

Options :
  A) Nouvelle instance MLflow dédiée (nouveau Space, nouvelle base)
  B) Instance MLflow partagée, isolation par projet PostgreSQL

Problème de l'option A :
  Coût additionnel (Space HF, nouvelle instance Neon).
  Duplication d'infrastructure pour un besoin identique.
  Maintenance de deux instances MLflow en parallèle.

Décision : option B — instance MLflow partagée
  - Isolation par projet PostgreSQL
  - Isolation par experiment name dans MLflow
  - Un seul artifact store S3, préfixes distincts par projet (.env PROJECT_NAME créé un dir dans le bucket)

Principe retenu :
  PostgreSQL comme système de namespaces — chaque projet possède ses schémas propres sur une instance partagée.
  Extensible : un schéma métier peut être adjoint à tout moment sans toucher au schéma MLflow.

Limite assumée :
  Couplage sur l'instance physique Neon.

Révision :
Date : 2026-05-05
  Décision initiale : instance MLflow partagée entre projets.
  Révisé : un Space MLflow dédié par projet.
  
  Motif : artifact store S3 partagé sans isolation par préfixe entraîne un mélange des artifacts entre projets.
  La séparation par experiment artifact_location est possible mais ajoute de la complexité à la configuration serveur.
  Un Space dédié est plus simple, plus sûr, et reste gratuit sur HF.

  PostgreSQL Neon reste partagé par schémas — pas de changement.
  S3 : préfixe dédié par Space MLflow (s3://bucket/theguardian/).

---
# ADR-003 — Notifications CI/CD : Discord webhook
Date : 2026-05-01
Contexte :
  Le pipeline Jenkins doit notifier l'équipe sur les événements de build (succès, échec). Trois options évaluées :
  Slack, email, Discord.

Slack :
  Webhook simple et bien documenté.
  Rejeté : compte workspace expiré, renouvellement payant pour un usage ponctuel de certification.

Email :
  Natif Jenkins via plugin emailext.
  Rejeté : nécessite un serveur SMTP configuré.

Décision : Discord webhook
  - Webhook permanent sans compte payant
  - Intégration triviale : curl POST vers l'URL du webhook
  - Suffisant comme POC

Limite assumée :
  Discord n'est pas un outil professionnel standard.

---
# ADR-004 — Pas de Docker Compose, supervisord dès le dev local
Date : 2026-05-01
Contexte :
  Cible de déploiement : HF Spaces (un conteneur, un port, pas de réseau).
  
Problème Docker Compose en staging :
  Modélise une architecture microservices qui ne peut pas exister en prod.
  Le gap local → prod crée des bugs d'intégration invisibles en dev.
  Fausse la compréhension de l'architecture réelle.

Décision : supervisord en local et en prod, même configuration
  - Parité dev/prod maximale
  - Un seul artefact à tester et déployer
  - Pattern déjà validé sur le projet fraud-detection

Limite assumée :
  Supervisord n'est pas une solution microservices.
  Ce compromis est acceptable car HF Spaces ne supporte pas une vraie architecture microservices de toute façon.
  Sur une cible VM ou K8s, Docker Compose ou Helm seraient préférables.

---
# ADR-005 — Supervisord plutôt que start.sh pour la gestion des processus
Date : 2026-05-01
Contexte :
  Le Space HF doit faire tourner nginx, uvicorn et streamlit
  dans un seul conteneur (contrainte HF Spaces : un seul port exposé).

Problème de start.sh :
  Gestion manuelle des processus avec & et wait.
  Pas de restart automatique sur crash.
  Pas de supervision des logs par processus.
  Ordre de démarrage non garanti.

Décision : supervisord
  - Restart automatique configurable par processus
  - Logs séparés par service
  - Ordre de démarrage déterministe (priority=)
  - Pattern validé en production sur le projet fraud-detection

Alternatives rejetées :
  - start.sh : fragile, pas de supervision
  - Docker Compose : non disponible dans HF Spaces (un seul conteneur) (déjà décidé)
  - systemd : non disponible dans les conteneurs HF

---
# ADR-006 — Choix du chargement du modèle (à la volée ou en cache)
Date : 2026-05-01
Contexte : Choix du mode d'inférence - chargement du modèle pour prédiction, à la volée ou depuis un cache

Contrainte : Pas de charge sur l'appel API, les prédictions sont journalières

Décision : Chargement à la volée
Conséquence : Latence additionnelle, mais inférence se fera toujours avec un modèle à jour

Alternatives rejetées :
- Chargement au premier appel, mis en cache en mémoire ensuite -> pb de la MàJ du modèle en cache (vérification de la version)
- Worker dédié : Inférence temps réel avec gestion de la charge (besoin de worker dédié + gestion externe du worker avec reload déclenché par superviseur pour MàJ du modèle en mémoire)

---
# ADR-007 — Workers externes, commandés via HTTP par Airflow
Date : 2026-05-01
### Contexte
Sur le projet fraud-detection, Airflow exécutait directement les tâches lourdes de ML (feature engineering, entraînement) via des PythonOperators.
Cela posait deux problèmes :

1. Couplage fort : la logique métier ML était embarquée dans les DAGs (ex: feat. engineering) ou devait être dupliquée entre DAGs et workers.

2. Compute lourd dans l'orchestrateur : Airflow n'est pas conçu pour exécuter des traitements ML intensifs — c'est un orchestrateur, pas un moteur de calcul.

### Contrainte d'infrastructure

Airflow tourne en local (Docker Compose).
Les workers tournent sur HF Space (conteneur distant).
Airflow ne peut pas accéder directement au filesystem du HF Space — la communication passe obligatoirement par HTTP (pythonOperators impossibles)

### Objectif architectural

Concentrer Airflow sur sa fonction d'orchestrateur pur.
Externaliser le compute ML dans des workers spécialisés.
Centraliser le code ML dans le conteneur manager — un seul endroit, pas de duplication (DRY).

### Séparation des responsabilités

supervisord → gère uniquement les services permanents (*_service)
FastAPI     → contrôle les workers ponctuels via subprocess (*_worker)
Airflow     → orchestre via HttpOperator, ne contient aucune logique ML

supervisord n'est pas conçu pour start/stop répétés à la demande — ce rôle est délégué à FastAPI qui lance les workers ponctuellement.

### Convention de nommage

*_service.py → processus permanent, enregistré dans supervisord
*_worker.py  → script ponctuel, lancé par FastAPI via subprocess

Avec Airflow et une comm par XCOM interne via des tasks, classiques vs le système choisi :

| Pattern Airflow classique | Pattern HTTP + PostgreSQL |
|---|---|
| `PythonOperator` retourne une valeur | FastAPI retourne `{ job_id, status }` |
| XCOM transporte la valeur | PostgreSQL sérialise l'état du job |
| Task suivante lit XCOM | Task Airflow poll `/status/{job_id}` |
| Enchaînement interne Airflow | DAG de polling + condition sur réponse HTTP |

### Principe du choix fait

Workers Python autonomes, exposés via FastAPI, commandés par Airflow via `HttpOperator`.

### Passage de valeurs entre tasks (XCOM)

Les workers ne peuvent pas pousser directement dans XCOM (contrairement à l'exécution via des pythonOperators) (pas d'accès à la base de métadonnées Airflow depuis HF Space). -> au moment où le process est lancé, fastapi envoie le numéro de job de suivi et un DAG va poll régulièrement pour assurer le suivi et récupérer les données pour les processus + Un autre DAG va lire les données XCOM depuis postgresql

Flux retenu :

  1. Airflow Task 1 → POST /run/transformers
                   ← { job_id: "abc123", status: "started" }
                   → xcom_push(job_id = "abc123")

  2. Worker (HF Space, arrière-plan)
     → traite le batch
     → écrit les résultats dans PostgreSQL (mlops-nyt-sentiment.scores)
     → écrit le statut dans PostgreSQL (mlops-nyt-sentiment.jobs)

  3. Airflow Task 2 → GET /status/abc123 (polling)
                   ← { status: "done", articles_processed: 142 }
                   → xcom_push(articles_processed = 142)

  4. Airflow Task 3 → lit XCOM pour décider de la suite
                     (ex: lancer prophet_worker si articles_processed > 0)

Ce qui transite où :
  PostgreSQL → données réelles (scores, forecasts, statuts de jobs) volumineuses, persistantes, consultées par l'API
  XCOM       → métadonnées de pilotage uniquement (job_id, counts, durée) légères, éphémères, utilisées entre tasks Airflow uniquement

Les scores ne passent jamais par XCOM.

### Airflow (local)

```
Airflow (local)
└── HttpOperator → POST /run/transformers  → démarre le worker
└── HttpOperator → GET  /status/{job_id}  → poll jusqu'à "done"
└── HttpOperator → POST /run/prophet      → idem
└── HttpOperator → POST /run/retrain      → idem
```

### Fonctionnement interne des DAGs

```
dag_infer
├── Task 1 : POST /run/feature_engineering → xcom_push(job_id)
├── Task 2 : GET  /status/{job_id}         → poll jusqu'à "done"
├── Task 3 : POST /run/transformers        → xcom_push(job_id)
└── Task 4 : GET  /status/{job_id}         → poll jusqu'à "done"

dag_forecast
├── Task 1 : POST /run/prophet             → xcom_push(job_id)
└── Task 2 : GET  /status/{job_id}         → poll jusqu'à "done"

dag_retrain
├── Task 1 : POST /run/feature_engineering → xcom_push(job_id)
├── Task 2 : GET  /status/{job_id}         → poll jusqu'à "done"
├── Task 3 : POST /run/retrain             → xcom_push(job_id)
└── Task 4 : GET  /status/{job_id}         → poll jusqu'à "done"
```

### HF Space — Manager

```
HF Space — manager
└── supervisord
    ├── nginx_service      → reverse proxy
    ├── api_service        → FastAPI : endpoints métier + /run/* + /status/*
    └── streamlit_service  → dashboard

FastAPI /run/*
  → subprocess.Popen(worker.py)
  → retourne job_id

FastAPI /status/{job_id}
  → lit PostgreSQL
  → retourne statut + métadonnées
```

### Compromis assumés

Avantages :
- Airflow découplé du compute ML
- Code ML centralisé, DRY, testable indépendamment
- Spécialisation claire des conteneurs

Inconvénients :
- Appel worker plus complexe qu'un PythonOperator local
- Nécessite un protocole de polling HTTP + gestion de job_id
- Latence réseau Airflow ↔ HF Space

### Limite

Si le use case évolue vers du temps réel, ce pattern HTTP polling devra être réévalué (WebSocket ou queue dédiée).


---
# ADR-008 — Initial feed via notebook, feed incrémental via worker
Date : 2026-05-05
Le chargement historique des articles Guardian (2017-2026) a été réalisé en one-shot depuis un notebook local.
Ce n'est pas un composant du système en production.

Le feed incrémental est intégré dans worker_transformers :
fetch → transform → insert → inférence dans le même process.

Justification : pas de valeur à séparer fetch et inférence pour un batch incrémental de faible volume (quelques dizaines d'articles par run horaire).