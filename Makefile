.DEFAULT_GOAL := help

# Import .env variables
include .env
export

# SOURCE DIRS
MLFLOW_SRC_DIR=_server-mlflow
REV_PROXY_DIR=_server-nginx
DASHBOARD_SRC_DIR=_server-streamlit


# DON'T CHANGE THESE NAMES
MLFLOW=mlflow

# DEPLOY DIRS
STAGING_DIR=_staging_app-server



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



# ====================================================
# Prod mode: HF Spaces deploy
# ====================================================
HFSPACES_DEPLOY_DIR=_HF-SPACES


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