import logging
from preproc.utils import save_image_to_s3
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import yaml
from preproc.processors.hit_or3c import HitOr3cProcessor
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import json
from PIL import Image
import io

def load_config(**context):
    import os
    DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
    def load_config(**context):
        import os
        DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)['preproc']
        context['task_instance'].xcom_push(key='config', value=config)

def load_mappings(**context):
    s3 = S3Hook()
    config = context['task_instance'].xcom_pull(key='config')
    bucket = config['s3']['base_path'].split('/')[-1]

    char_to_id = json.loads(s3.read_key(
        key='unified_char_to_id_mapping.json',
        bucket_name=bucket
    ))
    context['task_instance'].xcom_push(key='char_to_id', value=char_to_id)

def process_dataset(**context):
    config = context['task_instance'].xcom_pull(key='config')
    char_to_id = context['task_instance'].xcom_pull(key='char_to_id')
    test_mode = context['dag_run'].conf.get('test_mode', False)

    processor = HitOr3cProcessor(config)
    samples = processor.get_full_dataset()

    s3 = S3Hook()
    bucket = config['s3']['base_path'].split('/')[-1]

    stats = {
        'processed': 0,
        'errors': [],
        'chars_not_in_mapping': set(),
        'chars_not_in_font': set(),
        'processing_errors': {}
    }

    def save_checkpoint():
        checkpoint = {
            'processed_date': datetime.now().isoformat(),
            'total_processed': stats['processed'],
            'errors': stats['errors'],
            'chars_not_in_mapping': list(stats['chars_not_in_mapping']),
            'processing_errors': stats['processing_errors']
        }

        s3.load_string(
            string_data=json.dumps(checkpoint, indent=2, ensure_ascii=False),
            key=f"checkpoints/HIT_OR3C_checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            bucket_name=bucket
        )

    checkpoint_interval = 1000  # Save checkpoint every 1000 images

    # Process and save images
    for result in processor.process(char_to_id, samples, test_mode):
        if len(result) == 4:
            char_id, image, dataset_name, filename = result

            # Save to unified structure with proper path construction
            output_key = f"{config['s3']['output_dir']}/{char_id}/{dataset_name}_{filename}"

            if save_image_to_s3(s3, image, bucket, output_key):
                stats['processed'] += 1
            else:
                error_msg = f"Failed to save image {char_id}/{filename}"
                stats['errors'].append(error_msg)
                logging.error(error_msg)
                continue

    # Save processing report
    report = {
        'processed_date': datetime.now().isoformat(),
        'total_processed': stats['processed'],
        'errors': stats['errors'],
        'chars_not_in_mapping': list(stats['chars_not_in_mapping']),
        'processing_errors': stats['processing_errors']
    }

    s3.load_string(
        string_data=json.dumps(report, indent=2, ensure_ascii=False),
        key=f"reports/HIT_OR3C_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        bucket_name=bucket
    )

    return report

with DAG(
    'hit_or3c_preprocessing',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing']
) as dag:

    load_config_task = PythonOperator(
        task_id='load_config',
        python_callable=load_config
    )

    load_mappings_task = PythonOperator(
        task_id='load_mappings',
        python_callable=load_mappings
    )

    process_dataset_task = PythonOperator(
        task_id='process_dataset',
        python_callable=process_dataset
    )

    load_config_task >> load_mappings_task >> process_dataset_task
