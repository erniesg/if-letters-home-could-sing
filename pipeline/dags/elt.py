from datetime import datetime, timedelta
from airflow import DAG
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from pipeline.operators.download import DownloadOperator
from pipeline.operators.unzip import UnzipOperator
from pipeline.helpers.dynamodb import create_job, update_job_state, get_job_state
from pipeline.helpers.s3 import check_s3_object_exists, get_s3_object_info
from pipeline.helpers.config import get_config

settings = get_config()

def create_dataset_dag(dataset_name, default_args):
    with DAG(
        dag_id=f'{dataset_name}_elt',
        default_args=default_args,
        schedule_interval=None,
        catchup=False
    ) as dag:
        dataset_config = settings['datasets'][dataset_name]
        s3_config = settings['s3']

        start = DummyOperator(task_id='start')
        end = DummyOperator(task_id='end')

        def check_and_create_job(task_id, dataset_name, operation, **kwargs):
            job_id = f"{dataset_name}_{operation}_{kwargs['execution_date']}"
            job_state = get_job_state(job_id)
            if job_state and job_state['status'] == 'completed':
                print(f"Job {job_id} already completed. Skipping.")
                return 'skip'
            create_job(job_id, dataset_name, operation)
            return job_id

        def process_download(source, s3_bucket, s3_key, dataset_name, job_id, **kwargs):
            if check_s3_object_exists(s3_bucket, s3_key):
                file_info = get_s3_object_info(s3_bucket, s3_key)
                print(f"File already exists: {s3_key}")
                print(f"Size: {file_info['ContentLength']}, Type: {file_info['ContentType']}")
                update_job_state(job_id, status="completed", progress=100, metadata=file_info)
                return 'skip'

            download_op = DownloadOperator(
                task_id=f'download_{dataset_name}',
                dataset_name=dataset_name,
                source=source,
                s3_bucket=s3_bucket,
                s3_key=s3_key
            )
            result = download_op.execute(kwargs)
            update_job_state(job_id, status="completed", progress=100, metadata=result)
            return result

        def process_unzip(s3_bucket, s3_key, destination_prefix, dataset_name, unzip_password, job_id, **kwargs):
            if check_s3_object_exists(s3_bucket, destination_prefix):
                print(f"Destination already exists: {destination_prefix}")
                update_job_state(job_id, status="completed", progress=100)
                return 'skip'

            unzip_op = UnzipOperator(
                task_id=f'unzip_{dataset_name}',
                dataset_name=dataset_name,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                destination_prefix=destination_prefix,
                unzip_password=unzip_password
            )
            result = unzip_op.execute(kwargs)
            update_job_state(job_id, status="completed", progress=100, metadata=result)
            return result

        if isinstance(dataset_config['source']['path'], list):
            download_tasks = []
            unzip_tasks = []
            for i, path in enumerate(dataset_config['source']['path']):
                check_download = PythonOperator(
                    task_id=f'check_download_{dataset_name}_{i}',
                    python_callable=check_and_create_job,
                    op_kwargs={'task_id': f'download_{dataset_name}_{i}', 'dataset_name': dataset_name, 'operation': f'download_{i}'}
                )

                download_task = PythonOperator(
                    task_id=f'download_{dataset_name}_{i}',
                    python_callable=process_download,
                    op_kwargs={
                        'source': {'type': dataset_config['source']['type'], 'path': path},
                        's3_bucket': s3_config['bucket_name'],
                        's3_key': f"{s3_config['data_prefix']}/{dataset_name}_{i}.zip",
                        'dataset_name': dataset_name,
                        'job_id': "{{ task_instance.xcom_pull(task_ids='check_download_" + dataset_name + "_" + str(i) + "') }}"
                    }
                )

                check_unzip = PythonOperator(
                    task_id=f'check_unzip_{dataset_name}_{i}',
                    python_callable=check_and_create_job,
                    op_kwargs={'task_id': f'unzip_{dataset_name}_{i}', 'dataset_name': dataset_name, 'operation': f'unzip_{i}'}
                )

                unzip_task = PythonOperator(
                    task_id=f'unzip_{dataset_name}_{i}',
                    python_callable=process_unzip,
                    op_kwargs={
                        's3_bucket': s3_config['bucket_name'],
                        's3_key': f"{s3_config['data_prefix']}/{dataset_name}_{i}.zip",
                        'destination_prefix': f"{s3_config['processed_folder']}/{dataset_name}/{i}",
                        'dataset_name': dataset_name,
                        'unzip_password': dataset_config.get('unzip_password'),
                        'job_id': "{{ task_instance.xcom_pull(task_ids='check_unzip_" + dataset_name + "_" + str(i) + "') }}"
                    }
                )

                start >> check_download >> download_task >> check_unzip >> unzip_task
                download_tasks.append(download_task)
                unzip_tasks.append(unzip_task)

            # Add a final task to mark the entire dataset as processed
            final_check = PythonOperator(
                task_id=f'final_check_{dataset_name}',
                python_callable=check_and_create_job,
                op_kwargs={'task_id': f'final_{dataset_name}', 'dataset_name': dataset_name, 'operation': 'final'}
            )

            for unzip_task in unzip_tasks:
                unzip_task >> final_check

            final_check >> end

        else:
            check_download = PythonOperator(
                task_id=f'check_download_{dataset_name}',
                python_callable=check_and_create_job,
                op_kwargs={'task_id': f'download_{dataset_name}', 'dataset_name': dataset_name, 'operation': 'download'}
            )

            download_task = PythonOperator(
                task_id=f'download_{dataset_name}',
                python_callable=process_download,
                op_kwargs={
                    'source': dataset_config['source'],
                    's3_bucket': s3_config['bucket_name'],
                    's3_key': f"{s3_config['data_prefix']}/{dataset_name}.zip",
                    'dataset_name': dataset_name,
                    'job_id': "{{ task_instance.xcom_pull(task_ids='check_download_" + dataset_name + "') }}"
                }
            )

            check_unzip = PythonOperator(
                task_id=f'check_unzip_{dataset_name}',
                python_callable=check_and_create_job,
                op_kwargs={'task_id': f'unzip_{dataset_name}', 'dataset_name': dataset_name, 'operation': 'unzip'}
            )

            unzip_task = PythonOperator(
                task_id=f'unzip_{dataset_name}',
                python_callable=process_unzip,
                op_kwargs={
                    's3_bucket': s3_config['bucket_name'],
                    's3_key': f"{s3_config['data_prefix']}/{dataset_name}.zip",
                    'destination_prefix': f"{s3_config['processed_folder']}/{dataset_name}",
                    'dataset_name': dataset_name,
                    'unzip_password': dataset_config.get('unzip_password'),
                    'job_id': "{{ task_instance.xcom_pull(task_ids='check_unzip_" + dataset_name + "') }}"
                }
            )

            start >> check_download >> download_task >> check_unzip >> unzip_task >> end

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
            'retry_delay': timedelta(minutes=1),
        }
    )
