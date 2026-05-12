# Dockerfile used for back end server image
# Lightweight base image
FROM python:3.12-slim


# To avoid: Failed to import Git (the Git executable is not on the PATH)
# ->install  git
#RUN apt-get update && apt-get install -y git \
#    && rm -rf /var/lib/apt/lists/*
# Install system dependencies for debugging from within the container
RUN apt-get update && apt-get install -y \
    curl \
    lsof \
    net-tools \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Build time variables
# Define default value for deployment mode
# overriden by docker-compose set in variables
ARG PORT_FASTAPI_EXPOSED=7860

# ========================================
# USER CREATION
# ========================================
# Create a non-root user
RUN useradd -m -u 1000 user
USER user
# Define his environment
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH


# ========================================
# APPLICATION CONFIGURATION
# ========================================
# Set environment variables
# Possibly modified by Makefile commands

# Sets the working directory for the API
WORKDIR $HOME/app



# ========================================
# BUILD TIME
# ========================================
# Copy necessary files into the image
# In local development, they will be overwritten by a volume mount
# because the 'pipeline'  volume is bind-mounted via docker-compose
# Explicitly create working directories
# so they can be referred to in the WORKDIR directive
# REMEMBER: RUN, COPY, ADD are run as root by default in Docker
# NEED TO chown, chmod...


# requirements
# copy in WORKDIR $HOME/app
COPY --chown=user:user ./_server-fastapi/requirements.txt ./requirements.txt
COPY --chown=user:user ./_server-fastapi/requirements-torch.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements-torch.txt


# Set environment variables
ENV PROJECT_ROOT="/app"

# ========================================
# PYTHON PATH
# ========================================
# Make /app/pipeline importable as python module
# pipeline copied inside container in deploy mode
# OVERRIDEN by pipeline bind mounted as volume in docker-compose.yml
# Make ~/app/pipeline visible from within ~/app/src/*.py
ENV PYTHONPATH="${HOME}/app"

# ========================================
# RUNTIME
# ========================================
# Expose the port used by feed app
EXPOSE ${PORT_FASTAPI_EXPOSED}


# Command to launch FastAPI via Uvicorn
CMD ["sh", "-c", "uvicorn src.fastapi:app --host 0.0.0.0 --port=$PORT_FASTAPI_EXPOSED --reload"]