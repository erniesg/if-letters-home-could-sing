import os
import pytest
import boto3
from moto import mock_aws
from operators.download import DownloadOperator
from operators.unzip import UnzipOperator

MOCK_SETTINGS = {
    's3': {
        'bucket_name': 'test-bucket',
        'data_prefix': 'data',
        'processed_folder': 'processed'
    },
    'datasets': {
        'test-dataset': {
            'source': {
                'type': 'file',
                'path': '/Users/erniesg/Documents/archive_pw.zip'
            },
            'unzip_password': 'testPW'
        }
    }
}

@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture(scope="function")
def s3_bucket(s3):
    s3.create_bucket(Bucket=MOCK_SETTINGS['s3']['bucket_name'])
    yield MOCK_SETTINGS['s3']['bucket_name']

@mock_aws
def test_download_and_unzip_operator(s3_bucket):
    dataset_name = 'test-dataset'
    dataset_config = MOCK_SETTINGS['datasets'][dataset_name]
    s3_key = f"{MOCK_SETTINGS['s3']['data_prefix']}/{dataset_name}.zip"

    # Test DownloadOperator
    download_op = DownloadOperator(
        task_id='test_download',
        dataset_name=dataset_name,
        source=dataset_config['source'],
        s3_bucket=MOCK_SETTINGS['s3']['bucket_name'],
        s3_key=s3_key
    )
    file_info = download_op.execute(context={})

    print(f"Downloaded file info: {file_info}")
    assert file_info['file_size'] > 0, "Downloaded file is empty"
    assert file_info['is_zip'], "Downloaded file is not recognized as a ZIP archive"

    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.head_object(Bucket=MOCK_SETTINGS['s3']['bucket_name'], Key=s3_key)
    assert response['ContentLength'] == file_info['file_size']

    # Test UnzipOperator
    unzip_op = UnzipOperator(
        task_id='test_unzip',
        dataset_name=dataset_name,
        s3_bucket=MOCK_SETTINGS['s3']['bucket_name'],
        s3_key=s3_key,
        unzip_password=dataset_config['unzip_password']
    )
    unzip_op.execute(context={})

    # Check if files were unzipped and uploaded
    unzipped_prefix = f"{dataset_name}/"
    response = s3.list_objects_v2(Bucket=MOCK_SETTINGS['s3']['bucket_name'], Prefix=unzipped_prefix)

    assert 'Contents' in response, "No unzipped files found"
    unzipped_files = response['Contents']
    print(f"Number of unzipped files: {len(unzipped_files)}")
    print(f"Unzipped files: {[obj['Key'] for obj in unzipped_files]}")

    assert len(unzipped_files) > 0, "No files were unzipped"

    # Cleanup
    cleanup_s3(MOCK_SETTINGS['s3']['bucket_name'])
    response = s3.list_objects_v2(Bucket=MOCK_SETTINGS['s3']['bucket_name'])
    assert 'Contents' not in response, "Cleanup failed, objects still exist in the bucket"
    print("S3 bucket cleaned up successfully")

def cleanup_s3(bucket):
    s3 = boto3.client('s3', region_name='us-east-1')
    objects = s3.list_objects_v2(Bucket=bucket).get('Contents', [])
    if objects:
        delete_keys = {'Objects': [{'Key': obj['Key']} for obj in objects]}
        s3.delete_objects(Bucket=bucket, Delete=delete_keys)
