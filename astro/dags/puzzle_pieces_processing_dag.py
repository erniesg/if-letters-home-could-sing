from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import yaml
import os
import json
from collections import defaultdict
from tqdm import tqdm

# Get absolute path to config
DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

# Load config
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)['preproc']

def process_dataset(**context):
    s3 = S3Hook(aws_conn_id='aws_default')
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    dataset_config = config['datasets']['puzzle_pieces']
    
    print("\n" + "="*50)
    print("PUZZLE PIECES DATASET VERIFICATION")
    print("="*50)
    
    # 1. Verify base path - construct the correct path
    source_prefix = f"{config['s3']['unzipped_dir']}/puzzle-pieces-picker/Dataset/"
    print(f"\n1. Checking source path: s3://{bucket}/{source_prefix}")
    
    # Debug: Print the actual config values
    print("\nConfig values:")
    print(f"Base path: {config['s3']['base_path']}")
    print(f"Unzipped dir: {config['s3']['unzipped_dir']}")
    print(f"Dataset folder: {dataset_config['folder']}")
    
    # 2. List all contents to verify structure
    print("\n2. Listing directory structure...")
    try:
        # First, list the root unzipped directory
        root_contents = s3.list_keys(bucket_name=bucket, prefix=config['s3']['unzipped_dir'])
        print("\nRoot unzipped directory contents:")
        for item in root_contents:
            print(f"  - {item}")
            
        # Then list the puzzle pieces directory
        dataset_contents = s3.list_keys(bucket_name=bucket, prefix=source_prefix)
        print(f"\nDataset directory contents:")
        for item in dataset_contents:
            print(f"  - {item}")
            
        # Extract character folders
        char_folders = set()
        for obj in dataset_contents:
            relative_path = obj.replace(source_prefix, '')
            if '/' in relative_path:  # Has subdirectory
                char_id = relative_path.split('/')[0]
                char_folders.add(char_id)
        
        char_folders = sorted(list(char_folders))
        print(f"\nFound {len(char_folders)} character folders:")
        for folder in char_folders[:5]:  # Show first 5 folders
            print(f"  - {folder}")
            # List some contents of this folder
            folder_contents = [
                k for k in dataset_contents 
                if k.startswith(f"{source_prefix}{folder}/")
            ][:3]
            for item in folder_contents:
                print(f"    - {item}")
                
        if not char_folders:
            print("\nERROR: No character folders found!")
            return []
            
        # Continue with processing...

    except Exception as e:
        print(f"Error during dataset verification: {str(e)}")
        raise

    return results

def generate_report(**context):
    ti = context['task_instance']
    stats = ti.xcom_pull(key='processing_stats')

    if not stats:
        print("No processing stats available")
        return

    print("\nProcessing Summary:")
    print(f"Total character folders: {stats['total_folders']}")
    print(f"Total files: {stats['total_files']}")
    print(f"Successfully processed: {stats['processed_files']}")
    
    print(f"Total folders with errors: {len([k for k, v in stats['folder_errors'].items() if v])}")

    print("\nFile types processed:")
    for ext, count in stats['file_types'].items():
        print(f"  {ext}: {count}")

    print("\nCharacter frequency statistics:")
    print(f"Unique characters: {len(stats['char_frequencies'])}")
    print(f"Average samples per character: {stats['frequency_stats']['mean']:.2f}")
    print(f"Standard deviation: {stats['frequency_stats']['std_dev']:.2f}")
    print(f"\nMost frequent character:")
    print(f"  ID: {stats['frequency_stats']['max_char']['id']}: {stats['frequency_stats']['max_char']['count']} samples")
    print(f"\nLeast frequent character:")
    print(f"  ID: {stats['frequency_stats']['min_char']['id']}: {stats['frequency_stats']['min_char']['count']} samples")

    # Report folders with errors
    folders_with_errors = [k for k, v in stats['folder_errors'].items() if v]
    if folders_with_errors:
        print(f"\nFolders with errors ({len(folders_with_errors)}):")
        for folder_id in sorted(folders_with_errors):
            print(f"\nID: {folder_id}:")
            for error in stats['folder_errors'][folder_id]:
                print(f"  - {error}")

    return stats

def test_s3_access(**context):
    """Test task to verify S3 access and list contents"""
    s3 = S3Hook(aws_conn_id='aws_default')
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

# Create DAG
dag = DAG(
    'puzzle_pieces_processing',
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Process Puzzle Pieces dataset',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing', 'puzzle_pieces'],
)

process_task = PythonOperator(
    task_id='process_dataset',
    python_callable=process_dataset,
    provide_context=True,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    provide_context=True,
    dag=dag,
)

test_s3_task = PythonOperator(
    task_id='test_s3_access',
    python_callable=test_s3_access,
    dag=dag
)

process_task >> report_task
test_s3_task >> process_task
