import boto3
from io import BytesIO
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def upload_to_s3(content, bucket, s3_key):
    s3 = boto3.client('s3')
    try:
        s3.upload_fileobj(BytesIO(content), bucket, s3_key)
        logger.info(f"Successfully uploaded to s3://{bucket}/{s3_key}")
    except ClientError as e:
        logger.error(f"Error uploading to s3://{bucket}/{s3_key}: {str(e)}")
        # We're not raising the exception, allowing the process to continue

def download_from_s3(bucket, s3_key):
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        logger.info(f"Successfully downloaded from s3://{bucket}/{s3_key}")
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Error downloading from s3://{bucket}/{s3_key}: {str(e)}")
        return None  # Returning None allows the calling function to handle the error

def check_s3_object_exists(bucket, s3_key):
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            logger.error(f"Error checking s3://{bucket}/{s3_key}: {str(e)}")
            return False

def get_s3_object_info(bucket, s3_key):
    s3 = boto3.client('s3')
    try:
        response = s3.head_object(Bucket=bucket, Key=s3_key)
        return {
            'ContentLength': response.get('ContentLength', 0),
            'ContentType': response.get('ContentType', 'Unknown')
        }
    except ClientError as e:
        logger.error(f"Error getting info for s3://{bucket}/{s3_key}: {str(e)}")
        return None

def check_s3_prefix_exists(bucket, prefix):
    s3 = boto3.client('s3')
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except ClientError as e:
        logger.error(f"Error checking prefix s3://{bucket}/{prefix}: {str(e)}")
        return False

def list_s3_objects(bucket, prefix):
    s3 = boto3.client('s3')
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return response.get('Contents', [])
    except ClientError as e:
        logger.error(f"Error listing objects in s3://{bucket}/{prefix}: {str(e)}")
        return []
