FROM quay.io/astronomer/astro-runtime:12.4.0

# Install system dependencies
USER root
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Copy src and training_rave from include directory
COPY include/src /usr/local/airflow/src
COPY include/training_rave /usr/local/airflow/training_rave

# Install Python dependencies
COPY requirements.txt /usr/local/airflow/
RUN pip install -r /usr/local/airflow/requirements.txt

ENV AIRFLOW__WEBSERVER__SHOW_TRIGGER_FORM_IF_NO_PARAMS=True
ENV PYTHONPATH="${PYTHONPATH}:/usr/local/airflow"

USER astro
