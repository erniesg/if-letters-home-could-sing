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
    
    # Debug S3 paths
    print("\nDebugging S3 paths:")
    print(f"Base bucket: {bucket}")
    print(f"Dataset folder: {dataset_config['folder']}")
    
    # List all levels to debug
    levels = [
        config['s3']['unzipped_dir'],
        f"{config['s3']['unzipped_dir']}/puzzle-pieces-picker",
        f"{config['s3']['unzipped_dir']}/puzzle-pieces-picker/Dataset"
    ]
    
    for path in levels:
        print(f"\nChecking path: s3://{bucket}/{path}")
        try:
            # Try both prefixes and keys
            prefixes = list(s3.list_prefixes(bucket_name=bucket, prefix=path))
            keys = list(s3.list_keys(bucket_name=bucket, prefix=path))
            print(f"Prefixes found: {len(prefixes)}")
            print(f"Keys found: {len(keys)}")
            for p in prefixes:
                print(f"  Prefix: {p}")
            for k in keys:
                print(f"  Key: {k}")
        except Exception as e:
            print(f"Error listing {path}: {str(e)}")
    
    # Original path construction
    source_prefix = f"{config['s3']['unzipped_dir']}/{dataset_config['folder']}"
    dest_prefix = f"{config['s3']['output_dir']}"
    test_mode = context['dag_run'].conf.get('test_mode', False)
    sample_size = context['dag_run'].conf.get('sample_size', 3)

    print(f"\nSearching in bucket: {bucket}")
    print(f"Source prefix: {source_prefix}")
    print(f"Full S3 path: s3://{bucket}/{source_prefix}")

    # List and count all ID folders
    print("\nListing ID folders...")
    char_folders = s3.list_prefixes(bucket_name=bucket, prefix=source_prefix)
    
    if not char_folders:
        print(f"No folders found at s3://{bucket}/{source_prefix}")
        # List parent directory to debug
        parent_folders = s3.list_prefixes(bucket_name=bucket, prefix=config['s3']['unzipped_dir'])
        print(f"\nAvailable folders in {config['s3']['unzipped_dir']}:")
        for folder in parent_folders:
            print(f"- {folder}")
        return []

    stats = {
        'total_folders': len(char_folders),
        'total_files': 0,
        'processed_files': 0,
        'folder_errors': defaultdict(list),
        'file_types': defaultdict(int),
        'char_frequencies': defaultdict(int)
    }
    
    if test_mode:
        char_folders = list(char_folders)[:3]
        print(f"Test mode: Processing {len(char_folders)} folders")

    results = []

    with tqdm(total=len(char_folders), desc="Processing ID folders") as folder_pbar:
        for char_folder in char_folders:
            char_id = char_folder.rstrip('/').split('/')[-1]
            
            try:
                # List image files in folder
                files = [
                    key for key in s3.list_keys(bucket_name=bucket, prefix=char_folder)
                    if any(key.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])
                ]
                
                stats['total_files'] += len(files)
                stats['char_frequencies'][char_id] = len(files)

                for idx, source_key in enumerate(files, 1):
                    try:
                        ext = os.path.splitext(source_key)[1].lower()
                        stats['file_types'][ext] += 1

                        # Use consistent naming convention
                        dest_key = f"{dest_prefix}/{char_id}/puzzle_pieces_{char_id}_{idx}.png"
                        
                        s3.copy_object(
                            source_bucket=bucket,
                            source_key=source_key,
                            dest_bucket=bucket,
                            dest_key=dest_key
                        )

                        stats['processed_files'] += 1
                        results.append({
                            'char_id': char_id,
                            'status': 'success',
                            'source': source_key,
                            'destination': dest_key
                        })

                    except Exception as e:
                        error_msg = f"Failed to process file: {source_key} - {str(e)}"
                        stats['folder_errors'][char_id].append(error_msg)
                        print(f"\nError in folder {char_id}: {error_msg}")

            except Exception as e:
                error_msg = f"Failed to process folder: {str(e)}"
                stats['folder_errors'][char_id].append(error_msg)
                print(f"\nError in folder {char_id}: {error_msg}")

            folder_pbar.update(1)
            folder_pbar.set_postfix(processed=f"{stats['processed_files']}/{stats['total_files']}")

    # Calculate frequency statistics
    frequencies = list(stats['char_frequencies'].values())
    if frequencies:
        stats['frequency_stats'] = {
            'mean': sum(frequencies) / len(frequencies),
            'std_dev': (
                sum((x - (sum(frequencies) / len(frequencies))) ** 2 for x in frequencies) 
                / len(frequencies)
            ) ** 0.5,
            'max_char': {'id': max(stats['char_frequencies'].items(), key=lambda x: x[1])[0], 
                        'count': max(frequencies)},
            'min_char': {'id': min(stats['char_frequencies'].items(), key=lambda x: x[1])[0], 
                        'count': min(frequencies)}
        }

    # Cleanup in test mode
    if test_mode:
        print("\nTest mode: Cleaning up processed files...")
        for result in results:
            try:
                s3.delete_objects(bucket=bucket, keys=[result['destination']])
            except Exception as e:
                print(f"Error cleaning up {result['destination']}: {str(e)}")

    context['task_instance'].xcom_push(key='processing_stats', value=stats)
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
