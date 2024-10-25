import modal
from pathlib import Path
import sys
import os
import boto3
from botocore.exceptions import ClientError

# Add the parent directory to sys.path to allow imports from the src folder
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from src.config import ModalConfig
from src.app import create_modal_app, create_function
from src.utils import run_command
from training_rave.config import RAVEConfig
from training_rave.rave import get_train_command, get_preprocess_command

# Initialize ModalConfig
modal_config = ModalConfig(local_src_path=str(project_root / "src"))
print(f"Local src path: {modal_config.local_src_path}")

# Create Modal app, image, and volume
app, image, volume = create_modal_app(modal_config)

@create_function(app, modal_config, image, volume)
def train(config: RAVEConfig):
    print(f"Starting training with config: {config}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Contents of current directory: {os.listdir('.')}")

    # Debug AWS credentials
    print("Debugging AWS credentials:")
    print(f"AWS_ACCESS_KEY_ID: {'*' * len(os.environ.get('AWS_ACCESS_KEY_ID', ''))}")
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * len(os.environ.get('AWS_SECRET_ACCESS_KEY', ''))}")
    print(f"AWS_SESSION_TOKEN: {'*' * len(os.environ.get('AWS_SESSION_TOKEN', ''))}")

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
    output_path = local_s3_path / "output" / config.name

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

    # Download results from S3
    print("Downloading results")
    local_output_path = Path(f"./output/{base_config.name}")
    s3_results_path = f"output/{base_config.name}"
    s3_output_path = Path(f"{modal_config.s3_mount_path}/{s3_results_path}")
    print(f"Checking for results in S3 path: {s3_output_path}")

    if s3_output_path.exists():
        print(f"Contents of S3 output path: {list(s3_output_path.rglob('*'))}")
        for item in s3_output_path.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(s3_output_path)
                local_file_path = local_output_path / relative_path
                local_file_path.parent.mkdir(parents=True, exist_ok=True)
                local_file_path.write_bytes(item.read_bytes())
        print(f"Results downloaded to: {local_output_path}")
    else:
        print(f"No results found in S3 path: {s3_output_path}")

    print(f"Results path: {local_output_path}")

if __name__ == "__main__":
    modal.run(main)
