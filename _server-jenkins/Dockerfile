FROM jenkins/jenkins:2.541.3-jdk21
USER root

RUN apt-get update && apt-get install -y lsb-release curl

# Docker CLI
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
  https://download.docker.com/linux/debian/gpg
RUN echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
  https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
RUN apt-get update && apt-get install -y docker-ce-cli

# Python + utilitaires
RUN apt-get install -y python3 python3-pip jq
RUN python3 --version

USER jenkins
RUN jenkins-plugin-cli --plugins "blueocean docker-workflow"