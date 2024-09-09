from datetime import datetime, timedelta
from airflow import DAG
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from operators.download import DownloadOperator
from operators.unzip import UnzipOperator
import yaml
import os

# Load settings from YAML file
current_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(current_dir, '..', 'config', 'settings.yaml')
with open(settings_path, 'r') as file:
    settings = yaml.safe_load(file)

def create_dataset_dag(dataset_name, default_args):
    with DAG(
        dag_id=f'{dataset_name}_elt',
        default_args=default_args,
        schedule_interval=None,  # or set a specific schedule
        catchup=False
    ) as dag:
        dataset_config = settings['datasets'][dataset_name]
        s3_config = settings['s3']

        start = DummyOperator(task_id='start')

        if isinstance(dataset_config['source']['path'], list):
            download_tasks = []
            unzip_tasks = []
            for i, path in enumerate(dataset_config['source']['path']):
                download_task = DownloadOperator(
                    task_id=f'download_{dataset_name}_{i}',
                    dataset_name=dataset_name,
                    source={'type': dataset_config['source']['type'], 'path': path},
                    s3_bucket=s3_config['bucket_name'],
                    s3_key=f"{s3_config['data_prefix']}/{dataset_name}_{i}.zip"
                )
                download_tasks.append(download_task)

                unzip_task = UnzipOperator(
                    task_id=f'unzip_{dataset_name}_{i}',
                    dataset_name=dataset_name,
                    s3_bucket=s3_config['bucket_name'],
                    s3_key=f"{s3_config['data_prefix']}/{dataset_name}_{i}.zip",
                    destination_prefix=f"{s3_config['processed_folder']}/{dataset_name}",
                    unzip_password=dataset_config.get('unzip_password')
                )
                unzip_tasks.append(unzip_task)

            for download_task, unzip_task in zip(download_tasks, unzip_tasks):
                start >> download_task >> unzip_task
        else:
            download_task = DownloadOperator(
                task_id=f'download_{dataset_name}',
                dataset_name=dataset_name,
                source=dataset_config['source'],
                s3_bucket=s3_config['bucket_name'],
                s3_key=f"{s3_config['data_prefix']}/{dataset_name}.zip"
            )

            unzip_task = UnzipOperator(
                task_id=f'unzip_{dataset_name}',
                dataset_name=dataset_name,
                s3_bucket=s3_config['bucket_name'],
                s3_key=f"{s3_config['data_prefix']}/{dataset_name}.zip",
                destination_prefix=f"{s3_config['processed_folder']}/{dataset_name}",
                unzip_password=dataset_config.get('unzip_password')
            )

            start >> download_task >> unzip_task

        end = DummyOperator(task_id='end')

        if isinstance(dataset_config['source']['path'], list):
            for unzip_task in unzip_tasks:
                unzip_task >> end
        else:
            unzip_task >> end

    return dag

# Create a DAG for each dataset
for dataset in settings['datasets']:
    dag_id = f"{dataset}_elt_dag"
    globals()[dag_id] = create_dataset_dag(
        dataset,
        default_args={
            'owner': 'airflow',
            'start_date': datetime(2023, 1, 1),
            'retries': 3,
            'retry_delay': timedelta(minutes=5),
        }
    )
