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
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def load_config(**context):
    import os
    logging.info("Starting config load")
    DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'preproc' not in config:
                raise ValueError("Config file missing 'preproc' section")
            config = config['preproc']
            # Validate required config sections
            if not all(k in config for k in ['s3', 'datasets']):
                raise ValueError("Missing required config sections")
            logging.info("Config loaded successfully")
            context['task_instance'].xcom_push(key='config', value=config)
            return config
    except Exception as e:
        logging.error(f"Failed to load config: {str(e)}")
        raise

def load_mappings(**context):
    logging.info("Starting mappings load")
    s3 = S3Hook()

    config = context['task_instance'].xcom_pull(key='config')
    if not config:
        raise ValueError("No config found in XCom")

    # Correct bucket name extraction
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    logging.info(f"Using bucket: {bucket}")

    try:
        mapping_data = s3.read_key(
            key='unified_char_to_id_mapping.json',
            bucket_name=bucket
        )
        logging.info("Successfully read mapping file from S3")

        char_to_id = json.loads(mapping_data)
        logging.info(f"Loaded {len(char_to_id)} character mappings")

        context['task_instance'].xcom_push(key='char_to_id', value=char_to_id)
        return char_to_id
    except Exception as e:
        logging.error(f"Failed to load character mappings: {str(e)}")
        raise

def process_dataset(**context):
    config = context['task_instance'].xcom_pull(key='config')
    char_to_id = context['task_instance'].xcom_pull(key='char_to_id')
    test_mode = context['dag_run'].conf.get('test_mode', False)
    sample_size = context['dag_run'].conf.get('sample_size', 3)

    processor = HitOr3cProcessor(config=config)
    samples = processor.get_full_dataset()

    if test_mode:
        samples = samples[:sample_size]
        logging.info(f"Test mode: Processing {len(samples)} samples")
        processed_files = []

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

    # Add cleanup for test mode
    if test_mode:
        logging.info("Test mode: Cleaning up processed files...")
        for char_id, _, _, filename in processed_files:
            cleanup_key = f"{config['s3']['output_dir']}/{char_id}/{filename}"
            try:
                s3.delete_object(
                    bucket_name=bucket,
                    key=cleanup_key
                )
            except Exception as e:
                logging.error(f"Error cleaning up {cleanup_key}: {str(e)}")

    return report

def test_s3_access(**context):
    """Test task to verify S3 access and list contents"""
    s3 = S3Hook(aws_conn_id='aws_default')
    config = context['task_instance'].xcom_pull(key='config')
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    
    print(f"\nTesting S3 access to bucket: {bucket}")
    try:
        # Test bucket access
        buckets = s3.get_bucket(bucket)
        print(f"Successfully accessed bucket")
        
        # List root contents
        root_objects = s3.list_keys(bucket_name=bucket, prefix='')
        print("\nRoot contents:")
        for obj in root_objects:
            print(f"  - {obj}")
            
        # List unzipped directory
        unzipped = s3.list_keys(bucket_name=bucket, prefix='unzipped/')
        print("\nUnzipped directory contents:")
        for obj in unzipped:
            print(f"  - {obj}")
            
    except Exception as e:
        print(f"Error accessing S3: {str(e)}")
        raise

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

    test_s3_task = PythonOperator(
        task_id='test_s3_access',
        python_callable=test_s3_access,
        dag=dag
    )

    load_config_task >> load_mappings_task >> process_dataset_task >> test_s3_task
