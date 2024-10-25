import modal
from pathlib import Path
import sys
import os
import boto3
from botocore.exceptions import ClientError
import subprocess

# Add the parent directory to sys.path to allow imports from the src folder
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from src.config import ModalConfig
from src.app import create_modal_app, create_function
from src.utils import run_command, upload_to_volume, download_from_volume
from training_rave.config import RAVEConfig
from training_rave.rave import get_train_command, get_preprocess_command

# Initialize ModalConfig
modal_config = ModalConfig(local_src_path=str(project_root / "src"))
print(f"Local src path: {modal_config.local_src_path}")

# Create Modal app, image, and volume
app, image, volume = create_modal_app(modal_config)

@create_function(app, modal_config, image, volume)
def train(config: RAVEConfig):
    # Debugging mounts and volumes
    print("Debugging mounts and volumes:")
    print(f"Local volume path: {config.modal_config.volume_path}")
    print(f"S3 mount path: {config.modal_config.s3_mount_path}")

    print(f"Starting training with config: {config}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Contents of current directory: {os.listdir('.')}")

    # Debug AWS credentials
    print("Debugging AWS credentials:")
    print(f"AWS_ACCESS_KEY_ID: {'*' * len(os.environ.get('AWS_ACCESS_KEY_ID', ''))}")
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * len(os.environ.get('AWS_SECRET_ACCESS_KEY', ''))}")
    print(f"AWS_SESSION_TOKEN: {'*' * len(os.environ.get('AWS_SESSION_TOKEN', ''))}")

    # Debug RAVE installation
    print("Debugging RAVE installation:")
    try:
        pip_show_output = subprocess.check_output(["pip", "show", "acids-rave"], text=True)
        print(f"RAVE package information:\n{pip_show_output}")
    except subprocess.CalledProcessError:
        print("RAVE package not found via pip")

    print(f"Current PATH: {os.environ.get('PATH')}")
    print(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH')}")

    # Try to locate the rave command
    try:
        rave_path = subprocess.check_output(["which", "rave"], text=True).strip()
        print(f"RAVE command found at: {rave_path}")
    except subprocess.CalledProcessError:
        print("RAVE command not found in PATH")

    # Construct the S3 path using the correct config values
    s3_path = f"s3://{config.modal_config.s3_bucket_name}/{config.modal_config.s3_data_path}"
    print(f"Checking for dataset in S3 path: {s3_path}")

    # Initialize S3 client
    s3 = boto3.client('s3')

    try:
        # List objects in the S3 path
        response = s3.list_objects_v2(
            Bucket=config.modal_config.s3_bucket_name,
            Prefix=config.modal_config.s3_data_path
        )

        if 'Contents' in response:
            print(f"Dataset found in S3: {s3_path}")
            wav_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.wav')]
            print(f"Number of .wav files in dataset: {len(wav_files)}")
        else:
            raise FileNotFoundError(f"No objects found in S3 path: {s3_path}")

    except ClientError as e:
        print(f"Error accessing S3: {e}")
        raise

    # Local path where S3 is mounted
    local_s3_path = Path(f"{config.modal_config.s3_mount_path}")
    data_path = local_s3_path / config.modal_config.s3_data_path

    # Use Modal volume for output
    output_path = Path(config.modal_config.volume_path) / "output" / config.name

    # Check if the local volume and S3 mount paths exist
    if os.path.exists(config.modal_config.volume_path):
        print(f"Contents of local volume path: {os.listdir(config.modal_config.volume_path)}")
    else:
        print(f"Local volume path does not exist: {config.modal_config.volume_path}")

    if os.path.exists(config.modal_config.s3_mount_path):
        print(f"Contents of S3 mount path: {os.listdir(config.modal_config.s3_mount_path)}")
    else:
        print(f"S3 mount path does not exist: {config.modal_config.s3_mount_path}")

    print(f"Local S3 mount path: {local_s3_path}")
    print(f"Data path: {data_path}")
    print(f"Output path: {output_path}")
    print(f"Contents of data path: {os.listdir(data_path)}")

    # Ensure the output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Preprocess data
    preprocess_command = get_preprocess_command(config, data_path, output_path)
    print(f"Preprocess command: {' '.join(preprocess_command)}")
    run_command(preprocess_command)

    # Debug: List contents of the preprocessed directory
    preprocessed_path = output_path / "preprocessed"
    print(f"Contents of preprocessed directory: {list(preprocessed_path.rglob('*'))}")

    # Train model
    train_command = get_train_command(config, output_path)
    print(f"Train command: {' '.join(train_command)}")
    run_command(train_command)

    # List contents of the output directory
    print(f"Contents of output directory: {list(output_path.rglob('*'))}")

    # Ensure all changes are committed to the volume
    volume.commit()

    return f"Training completed for config: {config.name}. Results saved to {output_path}"

@app.local_entrypoint()
def main(
    dataset: str,
    name: str,
    channels: int = 1,
    lazy: bool = False,
    streaming: bool = False,
    max_steps: int = 10,
    smoke_test: bool = False,
    progress: bool = True,
):
    print(f"Main function called with arguments:")
    print(f"  dataset: {dataset}")
    print(f"  name: {name}")
    print(f"  channels: {channels}")
    print(f"  lazy: {lazy}")
    print(f"  streaming: {streaming}")
    print(f"  max_steps: {max_steps}")
    print(f"  smoke_test: {smoke_test}")
    print(f"  progress: {progress}")

    base_config = RAVEConfig(
        local_dataset=dataset,
        name=name,
        channels=channels,
        lazy=lazy,
        streaming=streaming,
        val_every=10,
        max_steps=max_steps,
        smoke_test=smoke_test,
        progress=progress,
        modal_config=modal_config
    )

    print(f"Created base config: {base_config}")

    print("Running single training job")
    result = train.remote(base_config)
    print(result)

    # Download results from Modal volume
    print("Downloading results")
    local_output_path = Path(f"./output/{base_config.name}")
    volume_results_path = f"output/{base_config.name}"
    download_from_volume(volume_results_path, str(local_output_path), volume)
    print(f"Results downloaded to: {local_output_path}")

    print(f"Results path: {local_output_path}")

if __name__ == "__main__":
    modal.run(main)
