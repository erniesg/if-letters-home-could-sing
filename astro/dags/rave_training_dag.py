from airflow.decorators import dag, task
from airflow.models import Connection
from airflow.utils.context import Context
from pendulum import datetime
import os
import sys
from pathlib import Path
import modal
import json
import boto3
from botocore.exceptions import ClientError
import subprocess
import modal

# Add project root to path for imports
project_root = Path("/usr/local/airflow")
sys.path.append(str(project_root))

from training_rave.config import RAVEConfig
from training_rave.rave import get_train_command, get_preprocess_command, get_export_command
from src.config import ModalConfig
from src.app import create_modal_app, create_function
from src.utils import run_command

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": 300,  # 5 minutes
}

@dag(
    dag_id="rave_training_smoke_test",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["rave", "training"],
)
def rave_training_dag():
    
    @task
    def setup_modal_auth(**context):
        """Set up Modal authentication using Airflow connections"""
        try:
            modal_conn = Connection.get_connection_from_secrets("modal_default")
            extra = json.loads(modal_conn.extra)
            
            os.environ["MODAL_TOKEN_ID"] = extra["token_id"]
            os.environ["MODAL_TOKEN_SECRET"] = extra["token_secret"]
            
            return {
                "auth_status": "success",
                "message": "Modal authentication configured successfully"
            }
        except Exception as e:
            context['task_instance'].xcom_push(
                key='error',
                value=f"Modal auth setup failed: {str(e)}"
            )
            raise

    @task
    def check_s3_data(**context):
        """Verify S3 data exists and is accessible"""
        try:
            # Get AWS credentials from Airflow connection
            aws_conn = Connection.get_connection_from_secrets("aws_default")
            
            # Set AWS credentials in environment
            os.environ["AWS_ACCESS_KEY_ID"] = aws_conn.login
            os.environ["AWS_SECRET_ACCESS_KEY"] = aws_conn.password
            if aws_conn.extra_dejson.get("aws_session_token"):
                os.environ["AWS_SESSION_TOKEN"] = aws_conn.extra_dejson["aws_session_token"]
            
            # Debug AWS credentials (masked)
            print("Debugging AWS credentials:")
            print(f"AWS_ACCESS_KEY_ID: {'*' * len(os.environ.get('AWS_ACCESS_KEY_ID', ''))}")
            print(f"AWS_SECRET_ACCESS_KEY: {'*' * len(os.environ.get('AWS_SECRET_ACCESS_KEY', ''))}")
            print(f"AWS_SESSION_TOKEN: {'*' * len(os.environ.get('AWS_SESSION_TOKEN', ''))}")
            
            s3 = boto3.client('s3')
            bucket_name = "if-letters-home-could-sing"
            data_path = "data/hainanese_opera"
            
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix=data_path
            )
            
            if 'Contents' in response:
                wav_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.wav')]
                return {
                    "status": "success",
                    "wav_count": len(wav_files),
                    "bucket": bucket_name,
                    "path": data_path
                }
            else:
                raise FileNotFoundError(f"No WAV files found in s3://{bucket_name}/{data_path}")
                
        except Exception as e:
            context['task_instance'].xcom_push(
                key='error',
                value=f"S3 data check failed: {str(e)}"
            )
            raise

    @task
    def initialize_training_config(s3_data: dict, **context):
        """Set up training configuration"""
        try:
            modal_config_dict = {
                "app_name": "rave",
                "local_src_path": str(project_root / "src"),
                "cpu_count": 16.0,
                "memory_size": 65536,
                "disk_size": None,
                "gpu": "T4",
                "s3_bucket_name": s3_data["bucket"],
                "s3_data_path": s3_data["path"],
                "volume_path": "/data",
                "s3_mount_path": "/s3-data",
                "pip_packages": [
                    "torch",
                    "tensorboard",
                    "acids-rave",
                    "torchaudio",
                    "boto3"
                ],
                "apt_packages": ["ffmpeg"]
            }

            rave_config_dict = {
                "local_dataset": "hainanese_opera",
                "name": "rave",
                "channels": 1,
                "batch_size": 8,
                "smoke_test": True,
                "progress": True,
                "max_steps": 1000,
                "val_every": 100,
                "save_every": 500
            }
            
            return {
                "modal_config": modal_config_dict,
                "rave_config": rave_config_dict
            }
        except Exception as e:
            context['task_instance'].xcom_push(
                key='error',
                value=f"Config initialization failed: {str(e)}"
            )
            raise

    @task
    def run_training(configs: dict, auth_status: dict, **context):
        """Execute RAVE training pipeline"""
        try:
            modal_config = ModalConfig(**configs["modal_config"])
            rave_config = RAVEConfig(**configs["rave_config"], modal_config=modal_config)
            
            # Create Modal app and resources
            app = modal.App("rave")
            
            # Create image with required packages
            image = (modal.Image.debian_slim()
                    .pip_install(*modal_config.pip_packages)
                    .apt_install(*modal_config.apt_packages))
            
            # Create volume using config
            volume = modal.Volume.from_name(
                modal_config.volume_name,  # Use config volume_name
                create_if_missing=True
            )
            
            # Create S3 mount
            s3_mount = modal.CloudBucketMount(
                modal_config.s3_bucket_name,
                secret=modal.Secret.from_name(modal_config.aws_secret_name)
            )
            
            @app.function(
                image=image,
                gpu=modal_config.gpu,
                volumes={
                    modal_config.volume_path: volume,
                    modal_config.s3_mount_path: s3_mount
                },
                secrets=[modal.Secret.from_name(modal_config.aws_secret_name)],
                timeout=modal_config.timeout
            )
            def train_remote(config: RAVEConfig):
                print("Starting train function")
                # Debug paths and mounts
                print(f"Local volume path: {config.modal_config.volume_path}")
                print(f"S3 mount path: {config.modal_config.s3_mount_path}")
                
                # Try to locate the rave command
                try:
                    rave_path = subprocess.check_output(["which", "rave"], text=True).strip()
                    print(f"RAVE command found at: {rave_path}")
                except subprocess.CalledProcessError:
                    print("RAVE command not found in PATH")
                
                # Set up paths
                local_s3_path = Path(config.modal_config.s3_mount_path)
                data_path = local_s3_path / config.modal_config.s3_data_path
                output_path = Path(config.modal_config.volume_path) / "output" / config.name
                
                # Run preprocessing if needed
                if not list((output_path / "preprocessed").glob("*")):
                    preprocess_command = get_preprocess_command(config, data_path, output_path)
                    print(f"Preprocess command: {' '.join(preprocess_command)}")
                    run_command(preprocess_command)
                
                # Train model
                train_command = get_train_command(config, output_path, config.max_steps, config.val_every)
                print(f"Train command: {' '.join(train_command)}")
                run_command(train_command)
                
                # Export variations
                runtime = datetime.now().strftime("%Y%m%d_%H%M%S")
                for streaming in [False, True]:
                    variation_config = RAVEConfig(**{**config.__dict__, "streaming": streaming})
                    variation_name = f"{config.name}_ch1_{'streaming' if streaming else 'non_streaming'}_{runtime}"
                    export_command = get_export_command(variation_config, output_path, variation_name)
                    print(f"Export command: {' '.join(export_command)}")
                    run_command(export_command)
                
                volume.commit()
                return {
                    "status": "success",
                    "output_path": str(output_path),
                    "runtime": runtime
                }
            
            # Execute the remote training
            result = train_remote.remote(rave_config)
            print(f"Training result: {result}")
            
            return result
            
        except Exception as e:
            context['task_instance'].xcom_push(
                key='error',
                value=f"Training failed: {str(e)}"
            )
            raise

    # Define task dependencies
    auth_result = setup_modal_auth()
    s3_data = check_s3_data()
    configs = initialize_training_config(s3_data)
    training_result = run_training(configs, auth_result)

# Instantiate the DAG
rave_training_dag()