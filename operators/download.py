import os
import requests
import mimetypes
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from helpers.s3 import check_s3_object_exists, get_s3_object_info, upload_to_s3

class DownloadOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        dataset_name,
        source,
        s3_bucket,
        s3_key,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.dataset_name = dataset_name
        self.source = source
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key

    def execute(self, context):
        if check_s3_object_exists(self.s3_bucket, self.s3_key):
            file_info = get_s3_object_info(self.s3_bucket, self.s3_key)
            self.log.info(f"File already exists: {self.s3_key}")
            self.log.info(f"Size: {file_info['ContentLength']}, Type: {file_info['ContentType']}")
            return file_info

        content, content_type = self._download_file()
        upload_to_s3(content, self.s3_bucket, self.s3_key)

        file_info = {
            'ContentLength': len(content),
            'ContentType': content_type
        }
        self.log.info(f"Downloaded and uploaded: {self.s3_key}")
        self.log.info(f"Size: {file_info['ContentLength']}, Type: {file_info['ContentType']}")

        return file_info

    def _download_file(self):
        source_type = self.source['type']
        source_path = self.source['path']

        if source_type == 'url':
            return self._download_from_url(source_path)
        elif source_type == 'file':
            return self._download_from_local(source_path)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _download_from_url(self, url):
        self.log.info(f"Downloading from URL: {url}")
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        return content, content_type

    def _download_from_local(self, file_path):
        self.log.info(f"Copying from local file: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local file not found: {file_path}")
        with open(file_path, 'rb') as file:
            content = file.read()
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        return content, content_type
