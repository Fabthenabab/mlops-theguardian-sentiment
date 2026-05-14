### creation
dags logs plugins

### creation .env
AIRFLOW_UID=1000

### Copie docker-compose.yaml
### Modification du build
### Supprimer les exemples
### Ajouter un volume partagé (bind mount) pour que les process puissent se transmettre des fichiers avec une référence commune

  x-airflow-common:
    &airflow-common
    #image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:3.1.8}     # A commenter
    build: .                                                # A décommenter
    environment:
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'                 # Passer à false
    volumes:
      # ADD SHARED VOLUME TO BE SURE THAT PROCESS ACCESS TO A COMMUNE REFERENCE DURING R/W OPs
      - ${AIRFLOW_PROJ_DIR:-.}/data:/opt/airflow/data

# Modification des services (port..)
### Port d'écoute du serveur Web
  services:
    airflow-apiserver:
      <<: *airflow-common
      command: api-server
      ports:
        - "9010:8080"

### Copie requirements.txt

### Copie Dockerfile

### Init AIRFLOW
docker compose run airflow-cli airflow config list

### Initialisation de la db
docker compose up airflow-init

# Lancer airflow
docker compose up -d --remove-orphans

