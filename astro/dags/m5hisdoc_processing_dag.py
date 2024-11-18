from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import yaml
import json
import logging
from pathlib import Path
import math
from collections import defaultdict
from PIL import Image
import io

def load_config(**context):
    DAG_FOLDER = Path(__file__).parent
    config_path = DAG_FOLDER / 'config' / 'preproc.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)['preproc']
    context['task_instance'].xcom_push(key='config', value=config)
    return config

def load_mappings(**context):
    s3 = S3Hook()
    config = context['task_instance'].xcom_pull(key='config')
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    
    # Load unified mapping
    mapping_data = s3.read_key(
        key='unified_char_to_id_mapping.json',
        bucket_name=bucket
    )
    char_to_id = json.loads(mapping_data)
    context['task_instance'].xcom_push(key='char_to_id', value=char_to_id)
    return char_to_id

def prepare_batches(**context):
    """Create batch manifests for Modal processing"""
    s3 = S3Hook()
    config = context['task_instance'].xcom_pull(key='config')
    char_to_id = context['task_instance'].xcom_pull(key='char_to_id')
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    dataset_config = config['datasets']['m5hisdoc']
    
    # Debug config
    logging.info(f"Using config: {json.dumps(config, indent=2)}")
    logging.info(f"Bucket: {bucket}")
    
    # Correct path handling for M5HisDoc
    source_prefix = f"{config['s3']['unzipped_dir']}/{dataset_config['folder']}/M5HisDoc_regular"
    images_prefix = f"{source_prefix}/images"
    labels_prefix = f"{source_prefix}/label_char"
    
    logging.info(f"Looking for images in: s3://{bucket}/{images_prefix}")
    logging.info(f"Looking for labels in: s3://{bucket}/{labels_prefix}")
    
    # List available prefixes for debugging
    available_prefixes = s3.list_prefixes(bucket_name=bucket, prefix=config['s3']['unzipped_dir'])
    logging.info(f"Available directories in {config['s3']['unzipped_dir']}:")
    for prefix in available_prefixes:
        logging.info(f"  - {prefix}")
    
    # List and validate image files
    images = sorted([
        key for key in s3.list_keys(bucket_name=bucket, prefix=images_prefix)
        if key.lower().endswith('.jpg')
    ])
    logging.info(f"Found {len(images)} image files")
    if not images:
        logging.warning("No images found! Listing parent directory:")
        parent_files = s3.list_keys(bucket_name=bucket, prefix=source_prefix)
        for f in parent_files:
            logging.info(f"  - {f}")
    
    # List and validate label files
    labels = sorted([
        key for key in s3.list_keys(bucket_name=bucket, prefix=labels_prefix)
        if key.lower().endswith('.txt')
    ])
    logging.info(f"Found {len(labels)} label files")
    
    # Match pairs with detailed logging
    image_label_pairs = []
    unmatched_images = []
    for img_path in images:
        expected_label = img_path.replace('/images/', '/label_char/').replace('.jpg', '.txt')
        if expected_label in labels:
            image_label_pairs.append((img_path, expected_label))
        else:
            unmatched_images.append(img_path)
            logging.warning(f"No matching label for image: {img_path}")
    
    logging.info(f"Successfully paired {len(image_label_pairs)} images with labels")
    if unmatched_images:
        logging.warning(f"Found {len(unmatched_images)} images without labels")
    
    # Test mode handling
    test_mode = context['dag_run'].conf.get('test_mode', False)
    sample_size = context['dag_run'].conf.get('sample_size', 3)
    
    if test_mode:
        logging.info(f"Test mode: Using {sample_size} image-label pairs")
        image_label_pairs = image_label_pairs[:sample_size]
        num_batches = min(3, math.ceil(len(image_label_pairs) / sample_size))
        logging.info(f"Test mode: Creating {num_batches} batches")
    else:
        num_batches = 100
    
    batch_size = math.ceil(len(image_label_pairs) / num_batches)
    logging.info(f"Batch size: {batch_size} pairs")
    
    # Create and save batch manifests
    batches = []
    for i in range(num_batches):
        manifest_key = f"batch_manifests/m5hisdoc/batch_{i:03d}.json"
        
        # Check if manifest already exists
        try:
            existing_manifest = s3.get_key(key=manifest_key, bucket_name=bucket)
            if existing_manifest:
                logging.info(f"Manifest {manifest_key} already exists, skipping creation")
                batches.append(manifest_key)
                continue
        except Exception:
            # Key doesn't exist, proceed with creation
            pass
            
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(image_label_pairs))
        batch_pairs = image_label_pairs[start_idx:end_idx]
        
        batch_manifest = {
            'batch_id': i,
            'config': {
                's3_bucket': bucket,
                'output_prefix': config['s3']['output_dir'],
                'dataset_name': 'M5HisDoc',
                'font_path': config['s3']['font'],
                'test_mode': test_mode
            },
            'char_to_id': char_to_id,
            'image_label_pairs': batch_pairs,
            'stats_output': f"stats/m5hisdoc/batch_{i:03d}_stats.json"
        }
        
        logging.info(f"Saving batch manifest {i} with {len(batch_pairs)} pairs")
        try:
            s3.load_string(
                string_data=json.dumps(batch_manifest, indent=2),
                key=manifest_key,
                bucket_name=bucket,
                replace=False  # Don't replace existing files
            )
            batches.append(manifest_key)
        except ValueError as e:
            if "already exists" in str(e):
                logging.info(f"Manifest {manifest_key} already exists, skipping")
                batches.append(manifest_key)
            else:
                raise
    
    context['task_instance'].xcom_push(key='batch_manifests', value=batches)
    return batches

def aggregate_stats(**context):
    """Aggregate stats from all batch processing"""
    s3 = S3Hook()
    config = context['task_instance'].xcom_pull(key='config')
    batch_manifests = context['task_instance'].xcom_pull(key='batch_manifests')
    bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
    
    aggregated_stats = {
        'total_images': 0,
        'total_chars': 0,
        'char_frequencies': defaultdict(int),
        'errors': [],
        'skipped': {
            'not_in_mapping': [],
            'not_in_font': [],
            'invalid_bbox': []
        },
        'dimensions': {
            'min_width': float('inf'),
            'max_width': 0,
            'min_height': float('inf'),
            'max_height': 0,
            'avg_width': 0,
            'avg_height': 0
        }
    }

    # Process batch stats
    for manifest_key in batch_manifests:
        try:
            stats_key = manifest_key.replace('batch_manifests', 'stats').replace('.json', '_stats.json')
            stats_data = s3.read_key(
                key=stats_key,
                bucket_name=bucket
            )
            batch_stats = json.loads(stats_data)
            
            # Aggregate numbers
            aggregated_stats['total_images'] += batch_stats.get('total_images', 0)
            aggregated_stats['total_chars'] += batch_stats.get('total_chars', 0)
            
            # Aggregate frequencies (convert from string keys)
            for char_id, freq in batch_stats.get('char_frequencies', {}).items():
                aggregated_stats['char_frequencies'][str(char_id)] += freq
            
            # Aggregate errors (already lists)
            aggregated_stats['errors'].extend(batch_stats.get('errors', []))
            
            # Aggregate skipped (convert sets to lists)
            aggregated_stats['skipped']['not_in_mapping'].extend(
                batch_stats.get('skipped', {}).get('not_in_mapping', [])
            )
            aggregated_stats['skipped']['not_in_font'].extend(
                batch_stats.get('skipped', {}).get('not_in_font', [])
            )
            aggregated_stats['skipped']['invalid_bbox'].extend(
                batch_stats.get('skipped', {}).get('invalid_bbox', [])
            )
            
            # Update dimensions
            dims = batch_stats.get('dimensions', {})
            aggregated_stats['dimensions']['min_width'] = min(
                aggregated_stats['dimensions']['min_width'],
                dims.get('min_width', float('inf'))
            )
            aggregated_stats['dimensions']['max_width'] = max(
                aggregated_stats['dimensions']['max_width'],
                dims.get('max_width', 0)
            )
            # ... similar for height ...
            
        except Exception as e:
            logging.error(f"Error processing stats from {manifest_key}: {str(e)}")
            continue

    # Prepare final report (ensure all data is JSON serializable)
    report = {
        'processed_date': datetime.now().isoformat(),
        'stats': {
            'total_images': aggregated_stats['total_images'],
            'total_chars': aggregated_stats['total_chars'],
            'char_frequencies': dict(aggregated_stats['char_frequencies']),
            'errors': aggregated_stats['errors'],
            'skipped': {
                'not_in_mapping': list(set(aggregated_stats['skipped']['not_in_mapping'])),
                'not_in_font': list(set(aggregated_stats['skipped']['not_in_font'])),
                'invalid_bbox': aggregated_stats['skipped']['invalid_bbox']
            },
            'dimensions': aggregated_stats['dimensions']
        }
    }

    # Save report
    report_key = f"reports/M5HisDoc_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    s3.load_string(
        string_data=json.dumps(report, indent=2, ensure_ascii=False),
        key=report_key,
        bucket_name=bucket
    )
    logging.info(f"Saved processing report to {report_key}")

    return report

def process_batch(**context):
    """Process a single batch of M5HisDoc images"""
    s3 = S3Hook()
    config = context['task_instance'].xcom_pull(key='config')
    batch_manifests = context['task_instance'].xcom_pull(key='batch_manifests')
    batch_id = context['task_instance'].task_id.split('_')[-1]
    manifest_key = batch_manifests[int(batch_id)]
    
    try:
        # Load batch manifest
        manifest_data = s3.read_key(
            key=manifest_key,
            bucket_name=bucket
        )
        manifest = json.loads(manifest_data)
        
        # Process each image-label pair
        batch_stats = {
            'total_images': 0,
            'total_chars': 0,
            'char_frequencies': defaultdict(int),
            'errors': [],
            'skipped': {
                'not_in_mapping': [],
                'not_in_font': [],
                'invalid_bbox': []
            }
        }
        
        for img_path, label_path in manifest['image_label_pairs']:
            try:
                # Read image
                img_data = s3.read_key(bucket_name=bucket, key=img_path)
                image = Image.open(io.BytesIO(img_data))
                
                # Read label
                label_data = s3.read_key(bucket_name=bucket, key=label_path)
                labels = label_data.strip().split('\n')
                
                # Process each character in label
                for char in labels:
                    if char in manifest['char_to_id']:
                        char_id = manifest['char_to_id'][char]
                        # Save to output
                        output_key = f"{manifest['config']['output_prefix']}/{char_id}/m5hisdoc_{batch_id}_{batch_stats['total_chars']}.png"
                        
                        # TODO: Add character extraction logic here
                        # For now, just save the whole image
                        success = save_image_to_s3(s3, image, bucket, output_key)
                        
                        if success:
                            batch_stats['total_chars'] += 1
                            batch_stats['char_frequencies'][char_id] += 1
                        else:
                            batch_stats['errors'].append(f"Failed to save {output_key}")
                    else:
                        batch_stats['skipped']['not_in_mapping'].append(char)
                
                batch_stats['total_images'] += 1
                
            except Exception as e:
                batch_stats['errors'].append(f"Error processing {img_path}: {str(e)}")
                continue
        
        # Save batch stats
        stats_key = manifest['stats_output']
        s3.load_string(
            string_data=json.dumps(batch_stats, indent=2),
            key=stats_key,
            bucket_name=bucket
        )
        
        return batch_stats
        
    except Exception as e:
        logging.error(f"Failed to process batch {batch_id}: {str(e)}")
        raise

def create_batch_tasks(dag):
    """Create processing tasks for each batch"""
    batch_tasks = []
    
    def create_batch_task(batch_id):
        return PythonOperator(
            task_id=f'process_batch_{batch_id}',
            python_callable=process_batch,
            provide_context=True,
            dag=dag
        )
    
    # Create tasks based on prepare_batches output
    ti = TaskInstance(dag.get_task('prepare_batches'), execution_date=datetime.now())
    batch_manifests = ti.xcom_pull(key='batch_manifests')
    
    if batch_manifests:
        for i in range(len(batch_manifests)):
            batch_tasks.append(create_batch_task(i))
    
    return batch_tasks

# Create DAG
dag = DAG(
    'm5hisdoc_processing',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['preprocessing']
)

load_config_task = PythonOperator(
    task_id='load_config',
    python_callable=load_config,
    dag=dag
)

load_mappings_task = PythonOperator(
    task_id='load_mappings',
    python_callable=load_mappings,
    dag=dag
)

prepare_batches_task = PythonOperator(
    task_id='prepare_batches',
    python_callable=prepare_batches,
    dag=dag
)

# Create batch processing tasks
batch_tasks = create_batch_tasks(dag)

aggregate_stats_task = PythonOperator(
    task_id='aggregate_stats',
    python_callable=aggregate_stats,
    dag=dag
)

# Set dependencies
load_config_task >> load_mappings_task >> prepare_batches_task
for batch_task in batch_tasks:
    prepare_batches_task >> batch_task >> aggregate_stats_task