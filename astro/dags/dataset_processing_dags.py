from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import yaml
import os
from tqdm import tqdm
from collections import defaultdict

# Get absolute path to config
DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

# Load config
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)['preproc']

# DAG configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def process_dataset(**context):
    from airflow.hooks.S3_hook import S3Hook

    s3 = S3Hook(aws_conn_id='aws_default')
    bucket = config['s3']['base_path'].split('/')[2]
    source_prefix = f"{config['s3']['unzipped_dir']}/puzzle_pieces/Dataset"
    dest_prefix = f"{config['s3']['output_dir']}"
    test_mode = context['dag_run'].conf.get('test_mode', False)

    # Initialize stats
    stats = {
        'total_characters': 0,
        'total_files': 0,
        'processed_files': 0,
        'folder_errors': defaultdict(list),  # Track errors by folder
        'file_types': defaultdict(int),
        'char_frequencies': {},
        'frequency_stats': {
            'mean': 0,
            'std_dev': 0,
            'max_char': {'id': None, 'char': None, 'count': 0},
            'min_char': {'id': None, 'char': None, 'count': float('inf')}
        }
    }

    # List and count all character ID folders with progress
    print("\nListing character folders...")
    char_folders = list(s3.list_prefixes(bucket_name=bucket, prefix=f"{source_prefix}/"))
    stats['total_folders'] = len(char_folders)
    if test_mode:
        char_folders = char_folders[:3]
        print(f"Test mode: Processing {len(char_folders)} folders")

    results = []
    # Load character mappings
    char_mappings_key = f"{config['s3']['data_dir']}/unified_id_to_char_mapping.json"
    char_mappings = json.loads(s3.read_key(char_mappings_key, bucket))

    # Track character frequencies
    char_frequencies = defaultdict(int)

    with tqdm(total=len(char_folders), desc="Processing character folders", position=0) as folder_pbar:
        for char_folder in char_folders:
            char_id = os.path.basename(os.path.normpath(char_folder))
            char = char_mappings.get(char_id, char_id)

            # List files in folder
            try:
                files = s3.list_keys(bucket_name=bucket, prefix=char_folder)
                files = [f for f in files if any(f.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])]
                stats['total_files'] += len(files)
                char_frequencies[char_id] = len(files)

                with tqdm(total=len(files), desc=f"Character {char} ({char_id})", position=1, leave=False) as file_pbar:
                    for idx, source_key in enumerate(files, 1):
                        try:
                            ext = os.path.splitext(source_key)[1].lower()
                            stats['file_types'][ext] += 1

                            dest_key = f"{dest_prefix}/{char_id}/puzzle_pieces_{char_id}_{idx}.png"
                            s3.copy_object(
                                source_bucket=bucket,
                                source_key=source_key,
                                dest_bucket=bucket,
                                dest_key=dest_key
                            )

                            stats['processed_files'] += 1
                            stats['char_stats'][char_id]['files'] += 1

                            results.append({
                                'char_id': char_id,
                                'status': 'success',
                                'source': source_key,
                                'destination': dest_key
                            })

                        except Exception as e:
                            error_msg = f"Failed to process file: {os.path.basename(source_key)} - {str(e)}"
                            stats['folder_errors'][char_id].append(error_msg)
                            print(f"\nError in folder {char_id}: {error_msg}")

                        file_pbar.update(1)

            except Exception as e:
                error_msg = f"Failed to process entire folder: {str(e)}"
                stats['folder_errors'][char_id].append(error_msg)
                print(f"\nError in folder {char_id}: {error_msg}")

            folder_pbar.update(1)
            folder_pbar.set_postfix(
                processed=f"{stats['processed_files']}/{stats['total_files']}"
            )

    # Calculate frequency statistics
    frequencies = list(char_frequencies.values())
    stats['char_frequencies'] = dict(char_frequencies)
    stats['frequency_stats']['mean'] = sum(frequencies) / len(frequencies)
    stats['frequency_stats']['std_dev'] = (
        sum((x - stats['frequency_stats']['mean']) ** 2 for x in frequencies) / len(frequencies)
    ) ** 0.5

    # Find min and max characters
    for char_id, freq in char_frequencies.items():
        char = char_mappings.get(char_id, char_id)
        if freq > stats['frequency_stats']['max_char']['count']:
            stats['frequency_stats']['max_char'] = {'id': char_id, 'char': char, 'count': freq}
        if freq < stats['frequency_stats']['min_char']['count']:
            stats['frequency_stats']['min_char'] = {'id': char_id, 'char': char, 'count': freq}

    # Cleanup in test mode
    if test_mode:
        print("\nTest mode: Cleaning up processed files...")
        for result in results:
            try:
                s3.delete_objects(bucket=bucket, keys=[result['destination']])
            except Exception as e:
                print(f"Error cleaning up {result['destination']}: {str(e)}")
    # Store detailed stats
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
    print(f"Total errors: {len(stats['errors'])}")

    print("\nFile types processed:")
    for ext, count in stats['file_types'].items():
        print(f"  {ext}: {count}")

    print("\nCharacter frequency statistics:")
    print(f"Unique characters: {len(stats['char_frequencies'])}")
    print(f"Average samples per character: {stats['frequency_stats']['mean']:.2f}")
    print(f"Standard deviation: {stats['frequency_stats']['std_dev']:.2f}")
    print(f"\nMost frequent character:")
    print(f"  {stats['frequency_stats']['max_char']['char']} (ID: {stats['frequency_stats']['max_char']['id']}): {stats['frequency_stats']['max_char']['count']} samples")
    print(f"\nLeast frequent character:")
    print(f"  {stats['frequency_stats']['min_char']['char']} (ID: {stats['frequency_stats']['min_char']['id']}): {stats['frequency_stats']['min_char']['count']} samples")

    # Report folders with errors
    folders_with_errors = [k for k, v in stats['folder_errors'].items() if v]
    if folders_with_errors:
        print(f"\nFolders with errors ({len(folders_with_errors)}):")
        for folder_id in sorted(folders_with_errors):
            char = char_mappings.get(folder_id, folder_id)
            print(f"\nCharacter {char} (ID: {folder_id}):")
            for error in stats['folder_errors'][folder_id]:
                print(f"  - {error}")

    return stats

# Create DAG
dag = DAG(
    'puzzle_pieces_processing',
    default_args=default_args,
    description='Process Puzzle Pieces dataset',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing', 'puzzle_pieces'],
)

# Define tasks
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

# Set task dependencies
process_task >> report_task
