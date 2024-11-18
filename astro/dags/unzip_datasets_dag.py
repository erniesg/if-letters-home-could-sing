from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook
from airflow.models import Variable
import os
import yaml
import zipfile
import rarfile
import io
from tqdm import tqdm
from pathlib import Path

DAG_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(DAG_FOLDER, 'config', 'preproc.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)['preproc']

def process_archive(archive_data, archive_type, password=None):
    """Process ZIP or RAR archive and yield file data"""
    if archive_type == 'zip':
        with zipfile.ZipFile(archive_data) as archive:
            if password:
                archive.setpassword(password)
            file_list = [f for f in archive.infolist() if not f.filename.endswith('/')]
            for file_info in file_list:
                with archive.open(file_info) as file:
                    yield file_info.filename, file.read()
    elif archive_type == 'rar':
        with rarfile.RarFile(archive_data) as archive:
            if password:
                archive.setpassword(password)
            file_list = [f for f in archive.infolist() if not f.isdir()]
            for file_info in file_list:
                yield file_info.filename, archive.read(file_info)
def unzip_dataset_to_s3(dataset_name, source_file, requires_password=False, **context):
    """
    Unzip dataset directly from source S3 to destination S3 location
    Skip if destination already exists (unless overwrite explicitly set to True)
    """
    s3 = S3Hook(aws_conn_id='aws_default')
    source_bucket = config['s3']['base_path'].split('/')[2]
    source_key = f"{config['s3']['data_dir']}/{source_file}"
    dest_prefix = f"{config['s3']['unzipped_dir']}/{dataset_name}"

    # Initialize stats
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_type': {},
    }

    # Check if already unzipped
    dest_objects = s3.list_keys(bucket_name=source_bucket, prefix=dest_prefix)
    if dest_objects and not context['dag_run'].conf.get('overwrite', False):
        print(f"\nDestination {dest_prefix} already exists, skipping...")
        # Get stats for existing files
        for obj_key in dest_objects:
            obj = s3.get_key(obj_key, bucket_name=source_bucket)
            if obj:
                stats['total_files'] += 1
                stats['total_size_bytes'] += obj.content_length
                ext = os.path.splitext(obj_key)[1].lower() or 'no_extension'
                stats['files_by_type'][ext] = stats['files_by_type'].get(ext, 0) + 1

        print("\nExisting files stats:")
        print(f"Total files: {stats['total_files']}")
        print(f"Total size: {stats['total_size_bytes'] / (1024*1024):.2f} MB")
        print("Files by type:")
        for ext, count in stats['files_by_type'].items():
            print(f"  {ext}: {count}")
        return

    # Get zip file from S3 with progress
    print(f"\nDownloading {source_file}...")
    zip_obj = s3.get_key(key=source_key, bucket_name=source_bucket)
    total_size = zip_obj.content_length
    
    # Download with progress bar
    zip_data = io.BytesIO()
    with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {source_file}") as pbar:
        for chunk in zip_obj.get()['Body'].iter_chunks(chunk_size=8192):
            zip_data.write(chunk)
            pbar.update(len(chunk))
    zip_data.seek(0)

    # Prepare zip extraction
    zip_args = {}
    if requires_password:
        zip_args['pwd'] = Variable.get("M5HISDOC_PASSWORD").encode()

    # Determine archive type and process
    archive_type = 'rar' if source_file.lower().endswith('.rar') else 'zip'
    password = Variable.get("M5HISDOC_PASSWORD").encode() if requires_password else None

    # For RAR files, we need to save temporarily
    if archive_type == 'rar':
        temp_path = '/tmp/temp_archive.rar'
        with open(temp_path, 'wb') as f:
            f.write(zip_data.getvalue())
        archive_source = temp_path
    else:
        archive_source = zip_data

    # Process and upload files
    try:
        file_list = list(process_archive(archive_source, archive_type, password))
        with tqdm(total=len(file_list), desc=f"Processing {dataset_name} files") as pbar:
            for filename, data in file_list:
                try:
                    pbar.set_postfix_str(f"Processing {os.path.basename(filename)}")

                    # Update stats
                    stats['total_files'] += 1
                    stats['total_size_bytes'] += len(data)
                    ext = os.path.splitext(filename)[1].lower() or 'no_extension'
                    stats['files_by_type'][ext] = stats['files_by_type'].get(ext, 0) + 1

                    # Upload to S3
                    dest_key = f"{dest_prefix}/{filename}"
                    s3.load_bytes(
                        bytes_data=data,
                        key=dest_key,
                        bucket_name=source_bucket,
                        replace=True
                    )
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    continue
    finally:
        # Cleanup temporary RAR file if created
        if archive_type == 'rar' and os.path.exists(temp_path):
            os.remove(temp_path)

    print(f"\nSuccessfully unzipped {source_file} to {dest_prefix}")
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_bytes'] / (1024*1024):.2f} MB")
    print("Files by type:")
    for ext, count in stats['files_by_type'].items():
        print(f"  {ext}: {count}")

    return stats

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
    description='Unzip all datasets to S3',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing', 'unzip'],
)

# Create unzip tasks for each dataset
for dataset_name, dataset_config in config['datasets'].items():
    unzip_task = PythonOperator(
        task_id=f'unzip_{dataset_name}',
        python_callable=unzip_dataset_to_s3,
        op_kwargs={
            'dataset_name': dataset_name,
            'source_file': dataset_config['file'],
            'requires_password': dataset_config.get('requires_password', False)
        },
        dag=dag,
    )
