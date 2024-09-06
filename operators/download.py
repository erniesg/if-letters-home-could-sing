import os
import requests
import mimetypes
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from helpers.s3 import upload_to_s3

class DownloadOperator(BaseOperator):
    @apply_defaults
    def __init__(self, dataset_name, source, s3_bucket, s3_key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset_name = dataset_name
        self.source = source
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key

    def execute(self, context):
        source_type = self.source['type']
        source_path = self.source['path']

        if source_type == 'file':
            content, content_type = self._handle_local_file(source_path)
        elif source_type == 'url':
            content, content_type = self._handle_url(source_path)
        else:
            raise ValueError(f"Invalid source type: {source_type}")

        file_info = self._process_and_upload(content, content_type)
        return file_info

    def _handle_local_file(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local file not found: {file_path}")
        with open(file_path, 'rb') as file:
            content = file.read()
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        return content, content_type

    def _handle_url(self, url):
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        return content, content_type

    def _process_and_upload(self, content, content_type):
        if len(content) == 0:
            raise ValueError("File is empty")

        file_size = len(content)
        self.log.info(f"File size: {file_size} bytes")
        self.log.info(f"File type: {content_type}")

        is_zip = content_type in ['application/zip', 'application/x-zip-compressed'] or self.s3_key.endswith('.zip')
        if is_zip:
            self.log.info("File appears to be a ZIP archive")
        else:
            self.log.warning("File does not appear to be a ZIP archive")

        upload_to_s3(content, self.s3_bucket, self.s3_key)
        self.log.info(f"Uploaded {self.dataset_name} dataset to S3")

        return {
            'file_size': file_size,
            'content_type': content_type,
            'is_zip': is_zip
        }
