from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook
from airflow.models import Variable
import yaml
import os

DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)['preproc']

from unzip_datasets_dag import unzip_dataset_to_s3  # Reuse the same function

dag = DAG(
    'unzip_m5hisdoc',
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Process M5HisDoc dataset',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing', 'm5hisdoc'],
)

# Single task for M5HisDoc with higher resources
unzip_task = PythonOperator(
    task_id='unzip_m5hisdoc',
    python_callable=unzip_dataset_to_s3,
    op_kwargs={
        'dataset_name': 'm5hisdoc',
        'source_file': config['datasets']['m5hisdoc']['file'],
        'requires_password': True
    },
    executor_config={
        "resources": {
            "memory_limit": "7G",
            "cpu_limit": "4"  # Use more CPU for faster processing
        }
    },
    dag=dag,
)