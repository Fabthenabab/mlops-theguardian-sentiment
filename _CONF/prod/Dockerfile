# Use a lightweight Python image
FROM python:3.12-slim


# ========================================
# USER CREATION
# ========================================
# Define User compatible with HF-Spaces file permissions
ARG USER_APP=user
ARG USER_GROUP=user-group
# Set user HOME dir for USER_APP
ENV HOME=/home/${USER_APP}
ENV USER_DATA=${HOME}/data
ENV PATH=${HOME}/.local/bin:$PATH

# Create a non-root user
RUN groupadd -g 1000 ${USER_GROUP} && \
    useradd -m -u 1000 -g ${USER_GROUP} ${USER_APP}

# ========================================
# INSTALL PACKAGES
# ========================================
# Install necessary tools
RUN apt-get update && apt-get install -y \
    supervisor \
    nginx \
    curl \
    lsof \
    net-tools \
    procps \
    git \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ========================================
# BUILD TIME
# ========================================

# ========================================
# DIR SETUP
# ========================================
# User

# System


# Copy necessary files into the image
# The same that are bind mounted into the image in docker-compose.yml
# Explicitly create working directories
# so they can be referred to in the WORKDIR directive
# REMEMBER: RUN, COPY, ADD are run as root by default in Docker
# NEED TO chown, chmod...
# Build time variables
# Define default value for deployment mode
# ADAPTED FROM ./_staging_app-server/manager-server in staging/Dockerfile 
ARG MANAGER_SERVER_DIR=./
ARG PORT_NGINX_EXPOSED=7860
ARG STARTUP_SCRIPT_DIR=/usr/local/bin


# ======================
# WORKDIR + REQUIREMENTS
# ======================
# User dir
RUN mkdir -p ${HOME}/app \
    && chown -R ${USER_APP}:${USER_GROUP} ${HOME}
# copy in WORKDIR $HOME/app
WORKDIR $HOME/app
# requirements
COPY ${MANAGER_SERVER_DIR}/requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir torch==2.11.0+cpu --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r ./requirements.txt

# ======================
# SUPERVISOR
# ======================
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/supervisord.conf ./supervisord.conf


# ======================
# LOGS
# ======================
# User logs
RUN mkdir -p ${HOME}/logs \
    && chown -R ${USER_APP}:${USER_GROUP} ${HOME}

# ======================
# NGINX
# ======================
# System
# create dirs used by nginx.conf/http
RUN mkdir -p \
    /tmp/nginx-client-body \
    /tmp/nginx-proxy \
    /tmp/nginx-fastcgi \
    /tmp/nginx-uwsgi \
    /tmp/nginx-scgi \
    /var/www/html \
    && chmod 777 /tmp/nginx* \
    && chmod 775 /var/www/html
# User logs
RUN mkdir -p ${HOME}/logs/nginx \
    && chown -R ${USER_APP}:${USER_GROUP} ${HOME}

COPY ${MANAGER_SERVER_DIR}/nginx.conf /etc/nginx/nginx.conf
COPY ${MANAGER_SERVER_DIR}/default.conf /etc/nginx/conf.d/default.conf
RUN chmod 644 /etc/nginx/conf.d/default.conf
# Copy html dir and files from mnt
COPY ${MANAGER_SERVER_DIR}/mnt/html /var/www/html


# ======================
# PIPELINE
# ======================
# pipeline
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/pipeline ./pipeline
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/pyproject.toml .
RUN pip install -e .

# ======================
# API
# ======================
# Create api dir
RUN mkdir -p ./api && \
    chown -R ${USER_APP}:${USER_GROUP} ./api
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/api ./api

# ======================
# STREAMLIT
# ======================
# User logs
RUN mkdir -p ${HOME}/logs/streamlit \
    && chown -R ${USER_APP}:${USER_GROUP} ${HOME}

# Create streamlit dir
RUN mkdir -p ./streamlit && \
    chown -R ${USER_APP}:${USER_GROUP} ./streamlit
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/streamlit/.streamlit ./streamlit/.streamlit
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/streamlit/src ./streamlit/src

# ======================
# WORKERS
# ======================
# Create _workers dir
RUN mkdir -p ./_workers && \
    chown -R ${USER_APP}:${USER_GROUP} ./_workers
COPY --chown=${USER_APP}:${USER_GROUP} ${MANAGER_SERVER_DIR}/_workers ./_workers

# ========================================
# PYTHON PATH
# ========================================
# Make /app/pipeline importable as python module
# Make ~/app/pipeline visible from within ~/app/streamlit/src/*.py
ENV PYTHONPATH="${HOME}/app/pipeline:${HOME}/app"


# ========================================
# RUNTIME
# ========================================
USER ${USER_APP}

# Expose the port used by nginx
EXPOSE ${PORT_NGINX_EXPOSED}

# Start services
# free unix socket that could still be in use by a previous run
RUN rm -f /tmp/supervisor.sock
CMD ["supervisord", "-c", "/home/user/app/supervisord.conf"]