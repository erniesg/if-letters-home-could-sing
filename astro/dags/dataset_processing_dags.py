from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from operators.extraction_operators import S3DownloadOperator, UnzipOperator
import yaml
import os

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
    from processors.puzzle_pieces import PuzzlePiecesProcessor

    # Get config and context
    temp_dir = context['task_instance'].xcom_pull(task_ids='unzip_dataset')
    test_mode = context['dag_run'].conf.get('test_mode', False)
    s3_output_base = f"{config['s3']['base_path']}/{config['s3']['output_dir']}"

    # Initialize processor
    processor = PuzzlePiecesProcessor(temp_dir=temp_dir)
    samples = processor.get_full_dataset()

    # If in test mode, only process a small sample
    if test_mode:
        samples = samples[:3]

    # Process and upload to S3
    results = []
    for result in processor.process(samples, s3_output_base):
        results.append(result)
        context['task_instance'].xcom_push(
            key=f"processed_{result['folder_id']}",
            value=result
        )

    return results

def generate_report(**context):
    # Get processing results
    ti = context['task_instance']
    results = ti.xcom_pull(task_ids='process_dataset')

    if not results:
        print("No results to report")
        return

    # Generate summary
    summary = {
        'total_processed': len(results),
        'folders_processed': len(set(r['folder_id'] for r in results)),
        'success_count': len([r for r in results if r['status'] == 'success']),
        'error_count': len([r for r in results if r['status'] != 'success'])
    }

    context['task_instance'].xcom_push(key='processing_stats', value=summary)

    print("\nProcessing Summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")

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
init_task = PythonOperator(
    task_id='init',
    python_callable=lambda: None,  # Placeholder for now
    dag=dag,
)

download_task = S3DownloadOperator(
    task_id='download_dataset',
    s3_path=f"{config['s3']['base_path']}/{config['s3']['data_dir']}/{config['datasets']['puzzle_pieces']['file']}",
    local_path='/tmp/puzzle_pieces.zip',
    dag=dag,
)

unzip_task = UnzipOperator(
    task_id='unzip_dataset',
    source_path='/tmp/puzzle_pieces.zip',
    target_path='/tmp/puzzle_pieces',
    dag=dag,
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

# Set task dependencies
init_task >> download_task >> unzip_task >> process_task >> report_task
