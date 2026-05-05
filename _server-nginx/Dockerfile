FROM nginx:latest

# Install utilities
RUN apt-get update && apt-get install -y \
    gettext-base \
    curl \
    iputils-ping \
    dnsutils \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*


#HEALTHCHECK CMD curl -f http://localhost/ || exit 1

# Build time variables
# Define default value for deployment mode
# overriden by docker-compose set in variables
ARG PORT_NGINX_EXPOSED=9100
ARG SERVER=./_server-nginx

# ========================================
# BUILD TIME
# ========================================
# Copy necessary files into the image
# In local development, they will be overwritten by a volume mount
# because copied dir/files 
# are bind-mounted via docker-compose
# Explicitly create working directories
# so they can be referred to in the WORKDIR directive
# REMEMBER: RUN, COPY, ADD are run as root by default in Docker
# NEED TO chown, chmod...


# Conf dir depends on base distrib (nginx:alpine vs nginx:latest)
#COPY ${SERVER}/mnt/default.conf /etc/nginx/conf.d/default.conf
# Use nginx built-in envsubst script to substitute .env var by their value
# default.conf.template is automatically copied in /etc/nginx/conf.d/default.conf 
COPY ${SERVER}/default.conf.template /etc/nginx/templates/default.conf.template
# Copy html dir and files
COPY ${SERVER}/html /var/www/html
COPY ${SERVER}/mnt/html /var/www/html


# ========================================
# RUNTIME
# ========================================
# Expose the port used by nginx
EXPOSE ${PORT_NGINX_EXPOSED}

# Command to run the nginx app
# ENTRYPOINT : /docker-entrypoint.sh
# Option 1
# CMD ["nginx", "-g", "daemon off;"]
# Option 2
# Specific script
# COPY entrypoint.sh /docker-entrypoint.d/40-custom.sh
# + default CMD
# Option 3
# + specific CMD
# CMD ["sh", "-c", "nginx -g 'daemon off;'"]