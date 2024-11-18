from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook
import os
import yaml
import rarfile

DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)['preproc']

def unzip_dataset_to_s3(dataset_name, source_file, **context):
    """Process datasets based on type"""
    s3 = S3Hook(aws_conn_id='aws_default')
    source_bucket = config['s3']['base_path'].split('/')[2]
    source_key = f"{config['s3']['data_dir']}/{source_file}"
    dest_prefix = f"{config['s3']['unzipped_dir']}/{dataset_name}"

    if source_file.lower().endswith('.rar'):
        # Handle RAR files locally (only for hit_or3c)
        handle_rar_file(s3, source_bucket, source_key, dest_prefix)
    else:
        # For ZIP files, we could use AWS native operations
        # This could be implemented using AWS Lambda or S3 Batch Operations
        raise NotImplementedError("Direct S3 unzip not implemented yet - would require AWS Lambda or S3 Batch Operations")

def handle_rar_file(s3, bucket, source_key, dest_prefix):
    """Handle RAR files which require local processing"""
    # Download RAR file
    print(f"Downloading RAR file...")
    rar_obj = s3.get_key(key=source_key, bucket_name=bucket)

    with open('/tmp/temp.rar', 'wb') as f:
        for chunk in rar_obj.get()['Body'].iter_chunks(chunk_size=1024*1024):
            f.write(chunk)

    # Extract and upload
    with rarfile.RarFile('/tmp/temp.rar') as rar:
        for info in rar.infolist():
            if not info.isdir():
                # Extract file
                data = rar.read(info.filename)
                # Upload to S3
                s3.load_bytes(
                    bytes_data=data,
                    bucket_name=bucket,
                    key=f"{dest_prefix}/{info.filename}",
                    replace=True
                )

    # Cleanup
    os.remove('/tmp/temp.rar')

# Create DAG
dag = DAG(
    'unzip_datasets',
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Unzip datasets',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing', 'unzip'],
)

# Only create task for RAR file (hit_or3c)
task = PythonOperator(
    task_id='unzip_hit_or3c',
    python_callable=unzip_dataset_to_s3,
    op_kwargs={
        'dataset_name': 'hit_or3c',
        'source_file': config['datasets']['hit_or3c']['file'],
    },
    executor_config={
        "resources": {
            "memory_limit": "4G",
            "cpu_limit": "2"
        }
    },
    dag=dag,
)
