FROM quay.io/astronomer/astro-runtime:12.4.0

# Install system dependencies
USER root
RUN apt-get update && \
    apt-get clean

# Copy preproc package to container
COPY include/preproc /usr/local/airflow/preproc
ENV AIRFLOW__WEBSERVER__SHOW_TRIGGER_FORM_IF_NO_PARAMS=True
# Add to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/usr/local/airflow"

USER astro
