.DEFAULT_GOAL := help

# Import .env variables
include .env
export

# SOURCE DIRS
MLFLOW_SRC_DIR=_server-mlflow
REV_PROXY_DIR=_server-nginx
DASHBOARD_SRC_DIR=_server-streamlit
FASTAPI_SRC_DIR=_server-fastapi
WORKERS_SRC_DIR=_workers
CONF_DIR=_CONF

# DON'T CHANGE THESE NAMES
MLFLOW=mlflow
MANAGER_SERVER=manager-server
DASHBOARD=streamlit
API=api


# DEPLOY DIRS
STAGING_DIR=_staging_app-server
HFSPACES_DEPLOY_DIR=_HF-SPACES



.PHONY: pre-build build clean
# ====================================================
# Dev mode: compose
# ====================================================
compose: ## Compose and start local development
# Build and Run services defined in ./docker-compose.yml
# Create 1 container for each service communicating on a docker network
# Using nginx rev proxy to transfer incoming requests to each service
# Use ./.env.dev
	$(eval include _CONF/dev/.env.dev)
	@echo "🚀 INCLUDING .env.dev"
	@echo "🚀 COMPOSING AND BUILDING LOCAL SERVICES IN CONTAINERS"
	@docker compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker compose rm -f 2>/dev/null || true
	@echo " => Cleaned containers and images: ✅"
	@docker image prune -f && echo " => Removed dangling images: ✅"
# Create _server-nginx/mnt
# For automatically created files and copied streamlit files
	@echo " => Create $(REV_PROXY_DIR)/mnt"
	@rm -rf $(REV_PROXY_DIR)/mnt && mkdir $(REV_PROXY_DIR)/mnt
	@cp -r $(REV_PROXY_DIR)/html/ $(REV_PROXY_DIR)/mnt/html/
# Copy common shared css betwwen streamlit and nginx
	@cp -r $(DASHBOARD_SRC_DIR)/src/assets/* $(REV_PROXY_DIR)/mnt/html/
	@docker compose build && echo " => Building WITH cache from last version of base image: ✅"
	@echo "🚀 Starting services..."
	@docker compose up --force-recreate && echo " => Application stopped: 🛑"

up: ## Start local development (3 containers)
	@echo "🚀 STARTING LOCAL SERVICES IN CONTAINERS"
	@echo "🚀 Starting services..."
	@docker compose up --force-recreate && echo " => Application stopped: 🛑"




# ====================================================
# Staging mode: pre-build
# ====================================================
pre-build:
# Create local dir and sub dirs for deployment
# First for staging mode as a test
# Ready to be committed on Hugging Face
# Will use 1 image and 1 container
# Each service defined in docker-compose.yml, now running in the same container
# Because cross communication between containers on HF Spaces
# with docker network is not possible for the moment
# And cross communication between containers over IP is impossible to achieve on HF Spaces
# 
# make pre-build is called by make build
	$(eval include _CONF/staging/.env.staging)
	@echo "🚀 CREATING STAGING DIR: $(STAGING_DIR)"
	@rm -rf $(STAGING_DIR) && mkdir -p $(STAGING_DIR) && echo " => Creating $(STAGING_DIR): ✅"


# Copy mlflow files
	@echo "[MLFLOW]"
	@cp -r $(MLFLOW_SRC_DIR)/ $(STAGING_DIR)/$(MLFLOW) 2>/dev/null || true && echo " => Copying $(MLFLOW_SRC_DIR)/ in $(STAGING_DIR)/$(MLFLOW): ✅"

# Prepare manager dir
	@echo "[MANAGER_SERVER]"
	@rm -rf $(STAGING_DIR)/$(MANAGER_SERVER) && mkdir -p $(STAGING_DIR)/$(MANAGER_SERVER) && echo " => Creating $(STAGING_DIR)/$(MANAGER_SERVER): ✅"
	@echo "[CONF STAGING FILES]"
	@cp $(CONF_DIR)/staging/README.md $(STAGING_DIR)/$(MANAGER_SERVER)/README.md  2>/dev/null || true && echo " => Copying $(CONF_DIR)/README.md in $(STAGING_DIR)/$(MANAGER_SERVER)/README.md: ✅"
	@echo "[REQUIREMENTS]"
	@cp $(CONF_DIR)/staging/requirements.txt $(STAGING_DIR)/$(MANAGER_SERVER)/requirements.txt  2>/dev/null || true && echo " => Copying $(CONF_DIR)/requirements.txt in $(STAGING_DIR)/$(MANAGER_SERVER)/requirements.txt: ✅"
	@cp $(FASTAPI_SRC_DIR)/requirements-torch.txt $(STAGING_DIR)/$(MANAGER_SERVER)/requirements-torch.txt  2>/dev/null || true && echo " => Copying $(FASTAPI_SRC_DIR)/requirements-torch.txt in $(STAGING_DIR)/$(MANAGER_SERVER)/requirements-torch.txt: ✅"
	@echo "[SUPERVISORD]"
	@cp $(CONF_DIR)/staging/supervisord.conf $(STAGING_DIR)/$(MANAGER_SERVER)/supervisord.conf  2>/dev/null || true && echo " => Copying $(CONF_DIR)/supervisord.conf in $(STAGING_DIR)/$(MANAGER_SERVER)/supervisord.conf: ✅"
# Copy nginx files: nginx.conf, default.conf.template (with envsubst), html/..
# Substitute directly env variables in default.conf.template
# because automatic envsubst from nginx entrypoint only works
# with nginx official image and not from nginx apt install
	@echo "[NGINX]"
	@mkdir $(STAGING_DIR)/$(MANAGER_SERVER)/mnt
	@cp -r $(REV_PROXY_DIR)/html/ $(STAGING_DIR)/$(MANAGER_SERVER)/mnt/html/ 2>/dev/null || true
	@cp -r $(DASHBOARD_SRC_DIR)/src/assets/* $(STAGING_DIR)/$(MANAGER_SERVER)/mnt/html/ 2>/dev/null || true
	@cp $(CONF_DIR)/staging/nginx.conf $(STAGING_DIR)/$(MANAGER_SERVER)/nginx.conf 2>/dev/null || true
	@envsubst '$$PORT_NGINX_EXTERNAL $$PROXY_PASS_DASHBOARD $$PROXY_PASS_API' \
		< $(REV_PROXY_DIR)/default.conf.template \
		> $(STAGING_DIR)/$(MANAGER_SERVER)/default.conf

# Copy api files
	@echo "[API]"
	@mkdir $(STAGING_DIR)/$(MANAGER_SERVER)/$(API)
	@cp -r $(FASTAPI_SRC_DIR)/src $(STAGING_DIR)/$(MANAGER_SERVER)/$(API)/  2>/dev/null || true && echo " => Copying $(FASTAPI_SRC_DIR)/src in $(STAGING_DIR)/$(MANAGER_SERVER)/$(API)/: ✅"

# Copy dashboard files
	@mkdir $(STAGING_DIR)/$(MANAGER_SERVER)/$(DASHBOARD)
	@cp -r $(DASHBOARD_SRC_DIR)/.streamlit $(STAGING_DIR)/$(MANAGER_SERVER)/$(DASHBOARD)/ 2>/dev/null || true && echo " => Copying $(DASHBOARD_SRC_DIR)/.streamlit in $(STAGING_DIR)/$(MANAGER_SERVER)/$(DASHBOARD)/: ✅"
	@cp -r $(DASHBOARD_SRC_DIR)/src $(STAGING_DIR)/$(MANAGER_SERVER)/$(DASHBOARD)/ 2>/dev/null || true && echo " => Copying $(DASHBOARD_SRC_DIR)/src in $(STAGING_DIR)/$(MANAGER_SERVER)/$(DASHBOARD)/: ✅"

# Copy workers
	@cp -r $(WORKERS_SRC_DIR) $(STAGING_DIR)/$(MANAGER_SERVER)// 2>/dev/null || true && echo " => Copying $(WORKERS_SRC_DIR) in $(STAGING_DIR)/$(MANAGER_SERVER)/: ✅"

# Copy pipeline files
	@cp -r pipeline $(STAGING_DIR)/$(MANAGER_SERVER)/ 2>/dev/null || true && echo " => Copying pipeline in $(STAGING_DIR)/$(MANAGER_SERVER)/: ✅"
	@cp pyproject.toml $(STAGING_DIR)/$(MANAGER_SERVER)/ 2>/dev/null || true && echo " => Copying pyproject.toml in $(STAGING_DIR)/$(MANAGER_SERVER)/: ✅"

# Copy Dockerfile
	@echo "[DOCKERFILE]"
	@cp -r $(CONF_DIR)/staging/Dockerfile $(STAGING_DIR)/$(MANAGER_SERVER)/Dockerfile  2>/dev/null || true && echo " => Copying $(CONF_DIR)/Dockerfile in $(STAGING_DIR)/$(MANAGER_SERVER)/Dockerfile: ✅"
	
# Remove __pycache__
	@echo "[CLEANING $(STAGING_DIR)]"
	@find $(STAGING_DIR) -type d -name '__pycache__' -exec rm -rf {} + \
		&& echo "=> Removing __pycache__ in $(STAGING_DIR): ✅"

# Empty HF-HFSPACES_DEPLOY_DIR
	@echo "[_HF-SPACES DIR]"
	@rm -rf $(HFSPACES_DEPLOY_DIR) && mkdir -p $(HFSPACES_DEPLOY_DIR) && echo " => Created $(HFSPACES_DEPLOY_DIR): ✅"

# ====================================================
# Staging mode: build, run
# ====================================================
# Build staging manager
build-manager: pre-build ## Build staging image
	@echo "🚀 BUILDING MANAGER DEPLOYMENT IMAGE"
	@docker build \
		-f ./$(STAGING_DIR)/$(MANAGER_SERVER)/Dockerfile \
		-t $(APP_IMG) . \
		&& echo " => Built image $(APP_IMG): ✅"











# ====================================================
# Prod mode: HF Spaces deploy
# ====================================================


# =================================================
push-mlflow: pre-build ## Deploy to HuggingFace Spaces
	$(eval include _CONF/prod/.env.prod)
	@echo "🤗 Push mlflow to HF SPACES"

	#	Clone if repo doesn't exist else pull
	@if [ ! -d "$(HFSPACES_DEPLOY_DIR)/$(MLFLOW)/.git" ]; then \
		echo " => Cloning HF repo..."; \
		git clone $(HF_SPACE_MLFLOW) $(HFSPACES_DEPLOY_DIR)/$(MLFLOW); \
		echo " => Repo cloned: ✅"; \
	else \
		echo " => Pulling latest from HF..."; \
		git -C $(HFSPACES_DEPLOY_DIR)/$(MLFLOW) pull; \
		echo " => Repo updated: ✅"; \
	fi

	@echo " => Copying files..."
	@rsync -av \
		--delete \
		--exclude='.git' \
		--exclude='README.md' \
		$(STAGING_DIR)/$(MLFLOW)/ $(HFSPACES_DEPLOY_DIR)/$(MLFLOW) > /dev/null 2>&1 || true
	@echo " => Files copied: ✅"
	@rm -rf $(STAGING_DIR)/$(MLFLOW) && \
		echo " => $(STAGING_DIR)/$(MLFLOW) removed: ✅"

	@echo "🔍 Git status:"
	@cd $(HFSPACES_DEPLOY_DIR)/$(MLFLOW) && git status --short

	@echo "📤 Pushing to HF Spaces..."
	@cd $(HFSPACES_DEPLOY_DIR)/$(MLFLOW) && \
		git add . && \
		if git diff --cached --quiet; then \
			echo " => No changes to push"; \
		else \
			git commit -m "Deploy: $$(date '+%Y-%m-%d %H:%M:%S')" && \
			git push && \
			echo " => Pushed to HF Spaces: ✅"; \
		fi

	@echo ""
	@echo "🎉 Deployment complete!"


# =================================================
push-manager: pre-build ## Deploy to HuggingFace Spaces
	$(eval include _CONF/prod/.env.prod)
	@echo "🤗 Push Manager server to HF SPACES"

# Create Manager-server dir in HF_DEPLOY_DIR
	@mkdir -p $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER) && echo " => Created $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER): ✅"

	#	Clone if repo doesn't exist else pull
	@if [ ! -d "$(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER)/.git" ]; then \
		echo " => Cloning HF repo..."; \
		git clone $(HF_SPACE_MANAGER) $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER); \
		echo " => Repo cloned: ✅"; \
	else \
		echo " => Pulling latest from HF..."; \
		git -C $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER) pull; \
		echo " => Repo updated: ✅"; \
	fi

	@echo " => Copying files..."
	@rsync -av \
		--delete \
		--exclude='.git' \
		$(STAGING_DIR)/$(MANAGER_SERVER)/ $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER) > /dev/null 2>&1 || true
	@echo " => Files copied: ✅"
# Replace staging Dockerfile by prod Dockerfile
	@rm -f $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER)/Dockerfile > /dev/null 2>&1 || true
	@cp -r $(CONF_DIR)/prod/Dockerfile $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER)/Dockerfile  2>/dev/null || true && echo " => staging Dockerfile replaced by prod: ✅"
	@rm -rf $(STAGING_DIR)/$(MANAGER_SERVER) && \
		echo " => $(STAGING_DIR)/$(MANAGER_SERVER) removed: ✅"

	@echo "🔍 Git status:"
	@cd $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER) && git status --short

	@echo "📤 Pushing to HF Spaces..."
	@cd $(HFSPACES_DEPLOY_DIR)/$(MANAGER_SERVER) && \
		git add . && \
		if git diff --cached --quiet; then \
			echo " => No changes to push"; \
		else \
			git commit -m "Deploy: $$(date '+%Y-%m-%d %H:%M:%S')" && \
			git push && \
			echo " => Pushed to HF Spaces: ✅"; \
		fi

	@echo ""
	@echo "🎉 Deployment complete!"