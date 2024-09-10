FROM quay.io/astronomer/astro-runtime:9.1.0

# Install dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the entire pipeline directory
COPY . /opt/airflow/pipeline

# Set the PYTHONPATH to include the pipeline directory
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow"
