import boto3
from io import BytesIO
from botocore.exceptions import ClientError
import logging
from pipeline.helpers.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
s3_client = boto3.client('s3', region_name=config['aws']['region'])

def upload_to_s3(content, bucket, s3_key):
    try:
        s3_client.upload_fileobj(BytesIO(content), bucket, s3_key)
        logger.info(f"Successfully uploaded to s3://{bucket}/{s3_key}")
    except ClientError as e:
        logger.error(f"Error uploading to s3://{bucket}/{s3_key}: {str(e)}")

def download_from_s3(bucket, s3_key):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        logger.info(f"Successfully downloaded from s3://{bucket}/{s3_key}")
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Error downloading from s3://{bucket}/{s3_key}: {str(e)}")
        return None

def check_s3_object_exists(bucket, s3_key):
    try:
        s3_client.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            logger.error(f"Error checking s3://{bucket}/{s3_key}: {str(e)}")
            return False

def get_s3_object_info(bucket, s3_key):
    try:
        response = s3_client.head_object(Bucket=bucket, Key=s3_key)
        return {
            'ContentLength': response.get('ContentLength', 0),
            'ContentType': response.get('ContentType', 'Unknown')
        }
    except ClientError as e:
        logger.error(f"Error getting info for s3://{bucket}/{s3_key}: {str(e)}")
        return None

def check_s3_prefix_exists(bucket, prefix):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except ClientError as e:
        logger.error(f"Error checking prefix s3://{bucket}/{prefix}: {str(e)}")
        return False

def list_s3_objects(bucket, prefix):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return response.get('Contents', [])
    except ClientError as e:
        logger.error(f"Error listing objects in s3://{bucket}/{prefix}: {str(e)}")
        return []

# Export the s3_client and all functions
__all__ = ['s3_client', 'upload_to_s3', 'download_from_s3', 'check_s3_object_exists',
           'get_s3_object_info', 'check_s3_prefix_exists', 'list_s3_objects']
