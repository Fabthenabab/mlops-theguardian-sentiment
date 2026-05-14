Data pipeline       → fetch, transform, insert, déduplication
ML inférence        → FinBERT, batch processing, cache
ML forecasting      → Prophet, time series, fenêtre glissante
MLflow              → versioning, registry, alias, tags
Monitoring          → Evidently, drift detection, snapshots S3
Orchestration       → Airflow, DAGs, HttpOperator, XCom, polling
API                 → FastAPI, lifespan, subprocess, jobs tracking
Dashboard           → Streamlit, fragments, polling, session state
CI/CD               → Jenkins, Discord, build, deploy HF Space
Infrastructure      → supervisord, nginx, Docker, HF Spaces

Décisions architecturales non triviales — workers externes commandés via HTTP, IPC via PostgreSQL, pas de Redis, parité dev/prod — qui ont toutes des implications en cascade sur le reste.


Oui — et c'est exactement la leçon que tu avais identifiée tôt dans cette conversation et que tu as traduite en décision architecturale documentée dans l'ADR-005.
Sur fraud tu avais :
Airflow DAG → PythonOperator → code ML dans le DAG
Worker predict → code ML dans le worker
→ duplication inévitable, pas de lib partagée
Sur Guardian tu as :
Airflow DAG → HttpOperator → Manager → worker ponctuel → pipeline/core/src/
→ code ML à un seul endroit, pas de duplication
Et le reload du modèle — sur fraud tu gérais un processus permanent avec cache + signal supervisord pour recharger. Sur Guardian tu as éliminé le problème par construction : pas de cache, pas de processus permanent, pas de signal à envoyer. Le worker charge le modèle, fait son travail, se termine. Le run suivant recharge automatiquement @production.
C'est une progression architecturale réelle et documentée — pas juste "j'ai fait pareil mais mieux", mais "j'ai identifié le problème fondamental et j'ai changé le pattern"