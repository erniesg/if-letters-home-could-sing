from airflow.models import BaseOperator
from pipeline.helpers.s3 import download_from_s3, upload_to_s3, check_s3_prefix_exists, list_s3_objects
from pipeline.helpers.dynamodb import update_job_state
from pipeline.helpers.config import get_config
import zipfile
import io

class UnzipOperator(BaseOperator):
    def __init__(self, dataset_name, s3_bucket, s3_key, destination_prefix, unzip_password=None, overwrite=False, **kwargs):
        super().__init__(**kwargs)
        self.dataset_name = dataset_name
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.destination_prefix = destination_prefix
        self.unzip_password = unzip_password
        self.overwrite = overwrite
        self.config = get_config()

    def execute(self, context):
        job_id = f"{self.dataset_name}_unzip_{context['execution_date']}"
        try:
            # Check if files are already unzipped
            if check_s3_prefix_exists(self.s3_bucket, self.destination_prefix):
                existing_files = list_s3_objects(self.s3_bucket, self.destination_prefix)
                self.log.info(f"Files already exist in destination: {self.destination_prefix}")
                self.log.info(f"Number of existing files: {len(existing_files)}")

                if not self.overwrite:
                    update_job_state(job_id, status='completed', progress=100, metadata={'existing_files': len(existing_files)})
                    return
                else:
                    self.log.info("Overwrite flag is set. Proceeding with unzip operation.")

            update_job_state(job_id, status='in_progress', progress=0)

            zip_content = download_from_s3(self.s3_bucket, self.s3_key)
            if not zip_content:
                raise ValueError(f"Failed to download zip file from s3://{self.s3_bucket}/{self.s3_key}")

            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
                total_files = len(zip_ref.namelist())
                for i, file in enumerate(zip_ref.namelist(), 1):
                    with zip_ref.open(file, pwd=self.unzip_password.encode() if self.unzip_password else None) as file_in_zip:
                        file_content = file_in_zip.read()
                        destination_key = f"{self.destination_prefix}/{file}"
                        upload_to_s3(file_content, self.s3_bucket, destination_key)

                    progress = int((i / total_files) * 100)
                    update_job_state(job_id, status='in_progress', progress=progress)

            update_job_state(job_id, status='completed', progress=100)
            self.log.info(f"Successfully unzipped and uploaded all files to s3://{self.s3_bucket}/{self.destination_prefix}/")
        except Exception as e:
            update_job_state(job_id, status='failed', progress=0, metadata={'error': str(e)})
            raise
