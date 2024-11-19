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

# Add project root to path for imports
project_root = Path("/usr/local/airflow")
sys.path.append(str(project_root))

from training_rave.config import RAVEConfig
from training_rave.rave import get_train_command, get_preprocess_command, get_export_command
from src.config import ModalConfig
from src.app import create_modal_app
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
            # Return only the necessary configuration as a dictionary
            modal_config_dict = {
                "app_name": "rave",
                "cpu_count": 4.0,
                "memory_size": 32768,
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
            
            # Create Modal app and volume
            app, image, volume = create_modal_app(modal_config)
            
            # Debug paths and mounts
            print("Debugging mounts and volumes:")
            print(f"Local volume path: {modal_config.volume_path}")
            print(f"S3 mount path: {modal_config.s3_mount_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Contents of current directory: {os.listdir('.')}")
            
            # Debug RAVE installation
            print("Debugging RAVE installation:")
            try:
                pip_show_output = subprocess.check_output(["pip", "show", "acids-rave"], text=True)
                print(f"RAVE package information:\n{pip_show_output}")
            except subprocess.CalledProcessError:
                print("RAVE package not found via pip")
            
            try:
                rave_path = subprocess.check_output(["which", "rave"], text=True).strip()
                print(f"RAVE command found at: {rave_path}")
            except subprocess.CalledProcessError:
                print("RAVE command not found in PATH")
            
            # Set up paths for commands
            local_s3_path = Path(modal_config.s3_mount_path)
            data_path = local_s3_path / modal_config.s3_data_path
            output_path = Path(modal_config.volume_path) / "output" / rave_config.name
            
            # Run preprocessing if needed
            preprocess_command = get_preprocess_command(rave_config, data_path, output_path)
            print(f"Preprocess command: {' '.join(preprocess_command)}")
            run_command(preprocess_command)
            
            # Train model
            train_command = get_train_command(rave_config, output_path, rave_config.max_steps, rave_config.val_every)
            print(f"Train command: {' '.join(train_command)}")
            run_command(train_command)
            
            # Export variations
            runtime = datetime.now().strftime("%Y%m%d_%H%M%S")
            for streaming in [False, True]:
                variation_config = RAVEConfig(**{
                    **rave_config.__dict__,
                    "streaming": streaming
                })
                variation_name = f"{rave_config.name}_ch1_{'streaming' if streaming else 'non_streaming'}_{runtime}"
                export_command = get_export_command(variation_config, output_path, variation_name)
                print(f"Export command for {variation_name}: {' '.join(export_command)}")
                run_command(export_command)
            
            # Debug final state
            print("\nFinal state:")
            print(f"Contents of volume path: {list(Path(modal_config.volume_path).glob('**/*'))}")
            print(f"Contents of S3 mount: {list(local_s3_path.glob('**/*'))}")
            
            volume.commit()
            return {
                "status": "success",
                "output_path": str(output_path),
                "runtime": runtime
            }
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