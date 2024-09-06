import io
import zipfile
import boto3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from helpers.s3 import upload_to_s3, download_from_s3

class UnzipOperator(BaseOperator):
    @apply_defaults
    def __init__(self, dataset_name, s3_bucket, s3_key, unzip_password=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset_name = dataset_name
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.unzip_password = unzip_password

    def execute(self, context):
        zip_content = download_from_s3(self.s3_bucket, self.s3_key)

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
            if self.unzip_password:
                zip_ref.setpassword(self.unzip_password.encode())

            for file_name in zip_ref.namelist():
                file_content = zip_ref.read(file_name)
                s3_file_key = f"{self.dataset_name}/{file_name}"
                upload_to_s3(file_content, self.s3_bucket, s3_file_key)
                self.log.info(f"Unzipped and uploaded: {s3_file_key}")

        self.log.info(f"Unzipped and uploaded all files for {self.dataset_name} dataset")
