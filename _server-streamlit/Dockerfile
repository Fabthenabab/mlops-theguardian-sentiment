# Use a lightweight Python image
FROM python:3.12-slim

# Install necessary tools
RUN apt-get update && apt-get install -y \
    nano \
    lsof \
    curl \
    net-tools \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Build time variables
# Define default value for deployment mode
# overriden by docker-compose set in variables
ARG PORT_STREAMLIT_EXPOSED=9101


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
# Modified by Makefile commands
ENV PORT_STREAMLIT_EXPOSED=${PORT_STREAMLIT_EXPOSED}

# Define streamlit env variables
ENV STREAMLIT_SERVER_PORT=${PORT_STREAMLIT_EXPOSED}
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
# Streamlit listens to URL/dashboard
# Streamlit automatically prepends '/' to STREAMLIT_SERVER_BASE_URL_PATH (as opposed to fastapi root_path=)
ENV STREAMLIT_SERVER_BASE_URL_PATH=dashboard

WORKDIR $HOME/app

# ========================================
# BUILD TIME
# ========================================
# Copy necessary files into the image
# In local development, they will be overwritten by a volume mount
# because the 'data' 'pipeline' 'streamlit' volumes
# are bind-mounted via docker-compose
# Explicitly create working directories
# so they can be referred to in the WORKDIR directive
# REMEMBER: RUN, COPY, ADD are run as root by default in Docker
# NEED TO chown, chmod...

# requirements
# copy in WORKDIR $HOME/app
COPY ./_server-streamlit/requirements.txt ./requirements.txt
# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt


# pipeline files
# Copy pipeline
COPY --chown=user:user ./pipeline ./pipeline

# _server-streamlit files
# Create streamlit dir
RUN mkdir -p ./streamlit && \
    chown -R user:user ./streamlit && \
    chmod -R g+w ./streamlit
# Copy _server-streamlit files
COPY --chown=user:user ./_server-streamlit/.streamlit ./streamlit/.streamlit
COPY --chown=user:user ./_server-streamlit/src ./streamlit/src


# Create cache directory (don't copy it)
RUN mkdir -p ./cache/ && \
    chown -R user:user ./cache && \
    chmod -R g+w ./cache


# ========================================
# PYTHON PATH
# ========================================
# Make /app/pipeline importable as python module
# pipeline copied inside container in deploy mode
# OVERRIDEN by pipeline bind mounted as volume in docker-compose.yml
# Make ~/app/pipeline visible from within ~/app/streamlit/src/*.py
ENV PYTHONPATH="${HOME}/app/pipeline:${HOME}/app"

# ========================================
# RUNTIME
# ========================================
# Expose the port used by Streamlit
EXPOSE ${PORT_STREAMLIT_EXPOSED}

# Command to run the Streamlit app
CMD ["sh", "-c", "streamlit run streamlit/src/dashboard.py --server.address=$STREAMLIT_SERVER_ADDRESS --server.port=$PORT_STREAMLIT_EXPOSED --server.baseUrlPath=$STREAMLIT_SERVER_BASE_URL_PATH"]