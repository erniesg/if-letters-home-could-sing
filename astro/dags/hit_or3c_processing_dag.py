from airflow import DAG
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.python import PythonOperator
from datetime import datetime
import yaml
import os
from preproc.processors.hit_or3c import HitOr3cProcessor
from preproc.utils import load_char_mappings
import json

# Load config
with open('dags/config/preproc.yaml', 'r') as f:
    config = yaml.safe_load(f)['preproc']

S3_BASE_PATH = config['s3']['base_path']
DATASET_NAME = 'hit_or3c'
DATASET_CONFIG = config['datasets'][DATASET_NAME]
DATASET_FOLDER = DATASET_CONFIG['folder']

def get_s3_path(*parts):
    return '/'.join([p.strip('/') for p in parts])

def load_unified_mappings(**context):
    s3 = S3Hook()
    bucket_name = S3_BASE_PATH.split('/')[-1]

    char_to_id = s3.read_key(
        key='unified_char_to_id_mapping.json',
        bucket_name=bucket_name
    )
    id_to_char = s3.read_key(
        key='unified_id_to_char_mapping.json',
        bucket_name=bucket_name
    )

    char_to_id = json.loads(char_to_id)
    id_to_char = json.loads(id_to_char)

    context['task_instance'].xcom_push(key='char_to_id', value=char_to_id)
    context['task_instance'].xcom_push(key='id_to_char', value=id_to_char)

def process_dataset(**context):
    s3 = S3Hook()
    bucket_name = S3_BASE_PATH.split('/')[-1]
    char_to_id = context['task_instance'].xcom_pull(key='char_to_id')

    # Input path in S3
    input_base_path = get_s3_path(config['s3']['unzipped_dir'], DATASET_FOLDER)

    processor = HitOr3cProcessor()
    samples = processor.get_full_dataset()

    stats = {
        'processed_chars': 0,
        'errors': [],
        'chars_not_in_mapping': set(),
        'chars_not_in_font': set()
    }

    for result in processor.process(char_to_id, samples):
        if len(result) == 4:
            char_id, image, dataset_name, filename = result

            # Save to unified structure
            output_key = get_s3_path(
                config['s3']['output_dir'],
                char_id,
                filename
            )

            # Save image to bytes
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            s3.load_bytes(
                bytes_data=img_byte_arr,
                key=output_key,
                bucket_name=bucket_name,
                replace=True
            )

            stats['processed_chars'] += 1
        else:
            char, _ = result
            stats['chars_not_in_mapping'].add(char)

    stats['chars_not_in_mapping'] = list(stats['chars_not_in_mapping'])
    stats['chars_not_in_font'] = list(processor.get_chars_not_in_font())

    context['task_instance'].xcom_push(key='processing_stats', value=stats)

def save_report(**context):
    s3 = S3Hook()
    bucket_name = S3_BASE_PATH.split('/')[-1]
    stats = context['task_instance'].xcom_pull(key='processing_stats')
    id_to_char = context['task_instance'].xcom_pull(key='id_to_char')

    report = {
        'dataset': DATASET_NAME,
        'folder': DATASET_FOLDER,
        'processed_date': datetime.now().isoformat(),
        'total_processed': stats['processed_chars'],
        'chars_not_in_mapping': stats['chars_not_in_mapping'],
        'chars_not_in_font': stats['chars_not_in_font']
    }

    report_key = get_s3_path(
        'reports',
        f"{DATASET_NAME}_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    s3.load_string(
        string_data=json.dumps(report, indent=2, ensure_ascii=False),
        key=report_key,
        bucket_name=bucket_name,
        replace=True
    )

with DAG(
    dag_id=f'{DATASET_NAME}_preprocessing',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing']
) as dag:

    load_mappings = PythonOperator(
        task_id='load_unified_mappings',
        python_callable=load_unified_mappings
    )

    process_dataset_task = PythonOperator(
        task_id='process_dataset',
        python_callable=process_dataset
    )

    save_report_task = PythonOperator(
        task_id='save_report',
        python_callable=save_report
    )

    load_mappings >> process_dataset_task >> save_report_task
