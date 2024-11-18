from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
import boto3
import zipfile
import os

class S3DownloadOperator(BaseOperator):
    @apply_defaults
    def __init__(self, s3_path, local_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.s3_path = s3_path
        self.local_path = local_path

    def execute(self, context):
        # Parse S3 path
        bucket = self.s3_path.split('/')[2]
        key = '/'.join(self.s3_path.split('/')[3:])

        # Create S3 client
        s3_client = boto3.client('s3')

        # Download file
        os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
        self.log.info(f"Downloading {self.s3_path} to {self.local_path}")
        s3_client.download_file(bucket, key, self.local_path)

        return self.local_path

class UnzipOperator(BaseOperator):
    @apply_defaults
    def __init__(self, source_path, target_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_path = source_path
        self.target_path = target_path

    def execute(self, context):
        self.log.info(f"Extracting {self.source_path} to {self.target_path}")
        os.makedirs(self.target_path, exist_ok=True)

        with zipfile.ZipFile(self.source_path, 'r') as zip_ref:
            zip_ref.extractall(self.target_path)

        # If in test mode, cleanup source file
        if context['dag_run'].conf.get('test_mode', False):
            os.remove(self.source_path)

        return self.target_path
