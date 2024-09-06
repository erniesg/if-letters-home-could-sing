import boto3
from io import BytesIO

def upload_to_s3(content, bucket, s3_key):
    s3 = boto3.client('s3')
    s3.upload_fileobj(BytesIO(content), bucket, s3_key)

def download_from_s3(bucket, s3_key):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=s3_key)
    return response['Body'].read()
