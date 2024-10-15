import os
import sys
import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timedelta
import time
from pipeline.operators.download import DownloadOperator
from pipeline.operators.unzip import UnzipOperator
from pipeline.helpers.dynamodb import create_job, update_job_state, get_job_state
from pipeline.helpers.config import get_config
from pipeline.helpers.s3 import s3_client, upload_to_s3

config = get_config()

MOCK_SETTINGS = {
    's3': config['s3'],
    'datasets': {
        'test-dataset': {
            'source': {
                'type': 'file',
                'path': '/Users/erniesg/Documents/archive_pw.zip'
            },
            'unzip_password': 'testPW',
            'overwrite': False
        }
    },
    'dynamodb': {
        'table_name': 'ETLJobTracker'
    },
    'aws': {
        'region': config['aws']['region']
    }
}

@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = MOCK_SETTINGS['aws']['region']

@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_aws():
        yield s3_client

@pytest.fixture(scope="function")
def dynamodb(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=MOCK_SETTINGS['aws']['region'])
        table = dynamodb.create_table(
            TableName=MOCK_SETTINGS['dynamodb']['table_name'],
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=MOCK_SETTINGS['dynamodb']['table_name'])
        yield dynamodb

@pytest.fixture(scope="function")
def s3_bucket(s3):
    s3.create_bucket(Bucket=MOCK_SETTINGS['s3']['bucket_name'],
                     CreateBucketConfiguration={'LocationConstraint': MOCK_SETTINGS['aws']['region']})
    yield MOCK_SETTINGS['s3']['bucket_name']

@mock_aws
def test_download_and_unzip_operator(s3_bucket, dynamodb):
    dataset_name = 'test-dataset'
    dataset_config = MOCK_SETTINGS['datasets'][dataset_name]
    s3_key = f"{MOCK_SETTINGS['s3']['data_prefix']}/{dataset_name}.zip"

    # Test DownloadOperator
    download_op = DownloadOperator(
        task_id='test_download',
        dataset_name=dataset_name,
        source=dataset_config['source'],
        s3_bucket=MOCK_SETTINGS['s3']['bucket_name'],
        s3_key=s3_key,
        overwrite=dataset_config.get('overwrite', False)
    )

    execution_date_1 = datetime(2023, 1, 1)
    job_id = f"{dataset_name}_download_{execution_date_1}"
    create_job(job_id, dataset_name, 'download')

    # First execution
    file_info = download_op.execute(context={'execution_date': execution_date_1})

    print(f"Downloaded file info: {file_info}")
    assert file_info['ContentLength'] > 0, "Downloaded file is empty"

    # Add a small delay to allow for job state update
    time.sleep(1)

    job_state = get_job_state(job_id)
    assert job_state['status'] == 'completed', f"Download job not marked as completed. Current status: {job_state['status']}"

    response = s3_client.head_object(Bucket=MOCK_SETTINGS['s3']['bucket_name'], Key=s3_key)
    assert response['ContentLength'] == file_info['ContentLength']

    # Second execution (should skip if overwrite is False)
    execution_date_2 = execution_date_1 + timedelta(days=1)
    file_info_2 = download_op.execute(context={'execution_date': execution_date_2})
    assert file_info_2 == file_info, "File should not have been re-downloaded"

    # Test UnzipOperator
    unzip_op = UnzipOperator(
        task_id='test_unzip',
        dataset_name=dataset_name,
        s3_bucket=MOCK_SETTINGS['s3']['bucket_name'],
        s3_key=s3_key,
        destination_prefix=f"{MOCK_SETTINGS['s3']['processed_folder']}/{dataset_name}",
        unzip_password=dataset_config['unzip_password'],
        overwrite=dataset_config.get('overwrite', False)
    )

    job_id = f"{dataset_name}_unzip_{execution_date_1}"
    create_job(job_id, dataset_name, 'unzip')

    # First execution
    unzip_op.execute(context={'execution_date': execution_date_1})

    # Add a small delay to allow for job state update
    time.sleep(1)

    job_state = get_job_state(job_id)
    assert job_state['status'] == 'completed', f"Unzip job not marked as completed. Current status: {job_state['status']}"

    # Check if files were unzipped and uploaded
    unzipped_prefix = f"{MOCK_SETTINGS['s3']['processed_folder']}/{dataset_name}/"
    response = s3_client.list_objects_v2(Bucket=MOCK_SETTINGS['s3']['bucket_name'], Prefix=unzipped_prefix)

    assert 'Contents' in response, "No unzipped files found"
    unzipped_files = response['Contents']
    print(f"Number of unzipped files: {len(unzipped_files)}")
    print(f"Unzipped files: {[obj['Key'] for obj in unzipped_files]}")

    assert len(unzipped_files) > 0, "No files were unzipped"

    # Second execution (should skip if overwrite is False)
    unzip_op.execute(context={'execution_date': execution_date_2})
    response_2 = s3_client.list_objects_v2(Bucket=MOCK_SETTINGS['s3']['bucket_name'], Prefix=unzipped_prefix)
    assert len(response_2['Contents']) == len(unzipped_files), "Files should not have been re-unzipped"

    # Cleanup
    cleanup_s3(MOCK_SETTINGS['s3']['bucket_name'])
    response = s3_client.list_objects_v2(Bucket=MOCK_SETTINGS['s3']['bucket_name'])
    assert 'Contents' not in response, "Cleanup failed, objects still exist in the bucket"
    print("S3 bucket cleaned up successfully")

def cleanup_s3(bucket):
    objects = s3_client.list_objects_v2(Bucket=bucket).get('Contents', [])
    if objects:
        delete_keys = {'Objects': [{'Key': obj['Key']} for obj in objects]}
        s3_client.delete_objects(Bucket=bucket, Delete=delete_keys)
