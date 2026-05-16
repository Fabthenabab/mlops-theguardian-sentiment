# ============================================================
#  _server-jenkins/Dockerfile
#  Jenkins LTS + Docker CLI + Python 3.13 + plugins
#
#  Base   : jenkins/jenkins:2.541.3-jdk21
#  Ports  : 9105:8080 (UI) | 9150:50000 (agents)
# ============================================================

FROM jenkins/jenkins:2.541.3-jdk21

USER root

# ────────────────────────────────────────
#  Dépendances système
# ────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    lsb-release \
    curl \
    jq \
    python3 \
    python3-pip \
    python3.13-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ────────────────────────────────────────
#  Docker CLI (pour DinD via docker-compose)
# ────────────────────────────────────────
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
        https://download.docker.com/linux/debian/gpg \
    && echo "deb [arch=$(dpkg --print-architecture) \
        signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
        https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ────────────────────────────────────────
#  Plugins Jenkins
#  blueocean      : UI pipeline moderne
#  docker-workflow: intégration Docker dans les pipelines
#  junit          : publication des rapports pytest (--junit-xml)
#  github         : webhook trigger sur push GitHub
# ────────────────────────────────────────
USER jenkins

RUN jenkins-plugin-cli --plugins \
    "blueocean \
    docker-workflow \
    junit \
    github"