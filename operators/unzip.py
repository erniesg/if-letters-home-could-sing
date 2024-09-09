import io
import zipfile
import boto3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from helpers.s3 import upload_to_s3, download_from_s3, check_s3_prefix_exists, list_s3_objects

class UnzipOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        dataset_name,
        s3_bucket,
        s3_key,
        destination_prefix,
        unzip_password=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.dataset_name = dataset_name
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.destination_prefix = destination_prefix
        self.unzip_password = unzip_password

    def execute(self, context):
        # Check if destination already exists
        if check_s3_prefix_exists(self.s3_bucket, self.destination_prefix):
            objects = list_s3_objects(self.s3_bucket, self.destination_prefix)
            total_size = sum(obj['Size'] for obj in objects)
            self.log.info(f"Destination already exists: {self.destination_prefix}")
            self.log.info(f"Number of files: {len(objects)}, Total size: {total_size} bytes")
            return

        zip_content = download_from_s3(self.s3_bucket, self.s3_key)

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
            if self.unzip_password:
                zip_ref.setpassword(self.unzip_password.encode())

            total_files = len(zip_ref.namelist())
            processed_files = 0

            for file_name in zip_ref.namelist():
                file_content = zip_ref.read(file_name)
                s3_file_key = f"{self.destination_prefix}/{file_name}"
                upload_to_s3(file_content, self.s3_bucket, s3_file_key)
                processed_files += 1
                if processed_files % 100 == 0:  # Log progress every 100 files
                    self.log.info(f"Progress: {processed_files}/{total_files} files processed")

        self.log.info(f"Unzipped and uploaded all files for {self.dataset_name} dataset")
        self.log.info(f"Total files processed: {total_files}")

    def on_kill(self):
        self.log.info(f"Unzip operation for {self.dataset_name} was killed.")
        # Add any cleanup operations here if needed
