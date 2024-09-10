import boto3
import time
from botocore.exceptions import ClientError
from pipeline.helpers.config import get_config

config = get_config()
dynamodb = boto3.resource('dynamodb', region_name=config['aws']['region'])
table = dynamodb.Table(config['dynamodb']['table_name'])

def create_job(job_id, dataset_name, operation):
    try:
        current_time = int(time.time())
        response = table.put_item(
            Item={
                'job_id': job_id,
                'dataset_name': dataset_name,
                'operation': operation,
                'status': 'pending',
                'progress': 0,
                'start_time': current_time,
                'end_time': None,
                'metadata': {}
            }
        )
        return response
    except ClientError as e:
        print(f"Error creating job: {e}")
        return None

def update_job_state(job_id, status=None, progress=None, metadata=None):
    try:
        update_expression = []
        expression_attribute_values = {}

        if status:
            update_expression.append('#s = :s')
            expression_attribute_values[':s'] = status

        if progress is not None:
            update_expression.append('progress = :p')
            expression_attribute_values[':p'] = progress

        if metadata:
            update_expression.append('metadata = :m')
            expression_attribute_values[':m'] = metadata

        if status == 'completed' or status == 'failed':
            update_expression.append('end_time = :et')
            expression_attribute_values[':et'] = int(time.time())

        response = table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET ' + ', '.join(update_expression),
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames={'#s': 'status'},
            ReturnValues="UPDATED_NEW"
        )
        return response
    except ClientError as e:
        print(f"Error updating job state: {e}")
        return None

def get_job_state(job_id):
    try:
        response = table.get_item(Key={'job_id': job_id})
        return response.get('Item')
    except ClientError as e:
        print(f"Error getting job state: {e}")
        return None

__all__ = ['create_job', 'update_job_state', 'get_job_state']
