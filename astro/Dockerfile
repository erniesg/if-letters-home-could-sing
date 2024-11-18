FROM quay.io/astronomer/astro-runtime:12.4.0

# Install unrar
USER root
RUN apt-get update && \
    apt-get install -y rar unrar-free
USER astro
