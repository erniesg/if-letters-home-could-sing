import modal
from pathlib import Path
import sys
import os
import boto3
from botocore.exceptions import ClientError
import subprocess
import yaml
from training_rave.rave import get_train_command, get_preprocess_command, get_export_command

# Add the parent directory to sys.path to allow imports from the src folder
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from src.config import ModalConfig
from src.app import create_modal_app, create_function
from src.utils import run_command, upload_to_volume, download_from_volume, read_file_from_volume, list_files_in_volume
from training_rave.config import RAVEConfig
from training_rave.rave import get_train_command, get_preprocess_command

# Initialize ModalConfig with custom resources
modal_config = ModalConfig(
    local_src_path=str(project_root / "src"),
    cpu_count=16.0,
    memory_size=65536,  # Use 64GB RAM
    disk_size=None  # Use ~200GB disk
)
print(f"Local src path: {modal_config.local_src_path}")

# Create Modal app, image, and volume
app, image, volume = create_modal_app(modal_config)

@create_function(app, modal_config, image, volume)
def train(config: RAVEConfig):
    print("Starting train function")
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
    preprocessed_path = output_path / "preprocessed"
    models_path = output_path / "models"

    # Ensure the output directories exist
    preprocessed_path.mkdir(parents=True, exist_ok=True)
    models_path.mkdir(parents=True, exist_ok=True)

    # Preprocess data if not already done
    if not list(preprocessed_path.glob("*")):
        preprocess_command = get_preprocess_command(config, data_path, output_path)
        print(f"Preprocess command: {' '.join(preprocess_command)}")
        run_command(preprocess_command)
    else:
        print("Preprocessed data already exists. Skipping preprocessing step.")

    # Get the training command (which now includes checkpoint detection)
    train_command = get_train_command(config, output_path, config.max_steps, config.val_every)

    print(f"Train command: {' '.join(train_command)}")
    run_command(train_command)

    # Additional debugging information after training
    print(f"Training completed. Checking output:")
    print(f"Contents of models directory: {os.listdir(output_path / 'models')}")

    # Export model variations
    from datetime import datetime
    runtime = datetime.now().strftime("%Y%m%d_%H%M%S")

    variations = [
        {"channels": 1, "streaming": False},
        {"channels": 1, "streaming": True},
    ]

    print(f"Starting model export for {len(variations)} variations")

    for variation in variations:
        variation_config = RAVEConfig(**{**config.__dict__, **variation})
        variation_name = f"{config.name}_ch{variation['channels']}_{'streaming' if variation['streaming'] else 'non_streaming'}_{runtime}"
        export_command = get_export_command(variation_config, output_path, variation_name)
        print(f"Export command for {variation_name}: {' '.join(export_command)}")
        run_command(export_command)

    print(f"Export completed. Checking output:")
    print(f"Contents of exported directory: {os.listdir(output_path / 'exported')}")

    # List contents of the output directory
    print(f"Contents of output directory: {list(output_path.rglob('*'))}")

    # Ensure all changes are committed to the volume
    volume.commit()

    return f"Training and export completed for config: {config.name}. Results saved to {output_path}"

@app.local_entrypoint()
def main(
    dataset: str,
    name: str,
    channels: int = 1,
    lazy: bool = False,
    streaming: bool = False,
    batch_size: int = 8,
    smoke_test: bool = False,
    progress: bool = True,
    fidelity: float = 0.999,
    max_steps: int = 6000000,
    save_every: int = 100000,
    val_every: int = 10000,  # Add validation interval parameter
):
    print(f"Main function called with arguments:")
    print(f"  dataset: {dataset}")
    print(f"  name: {name}")
    print(f"  channels: {channels}")
    print(f"  lazy: {lazy}")
    print(f"  streaming: {streaming}")
    print(f"  batch_size: {batch_size}")
    print(f"  smoke_test: {smoke_test}")
    print(f"  progress: {progress}")
    print(f"  val_every: {val_every}")

    base_config = RAVEConfig(
        local_dataset=dataset,
        name=name,
        channels=channels,
        lazy=lazy,
        streaming=streaming,
        batch_size=batch_size,
        smoke_test=smoke_test,
        progress=progress,
        modal_config=modal_config,
        fidelity=fidelity,
        save_every=save_every,
        val_every=val_every,  # Add this field
    )

    print(f"Created base config: {base_config}")

    print("Running single training job")
    result = train.remote(base_config)
    print(result)

    # Download results from Modal volume
    print("Attempting to download results using download_from_volume function")
    local_output_path = Path(f"./output/{base_config.name}")
    volume_results_path = f"output/{base_config.name}"

    variations = [
        f"ch1_non_streaming_{runtime}",
        f"ch1_streaming_{runtime}"
    ]

    try:
        # Attempt to download the entire output directory
        download_from_volume(volume_results_path, str(local_output_path), volume)
        print(f"Results downloaded to: {local_output_path}")

        # Attempt to specifically download the exported .ts files
        for variation in variations:
            exported_model_path = f"{volume_results_path}/exported/{base_config.name}_{variation}.ts"
            local_model_path = local_output_path / "exported" / f"{base_config.name}_{variation}.ts"

            try:
                local_model_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_model_path, 'wb') as f:
                    for chunk in volume.read_file(exported_model_path):
                        f.write(chunk)
                print(f"Exported model downloaded to: {local_model_path}")
            except Exception as e:
                print(f"Error downloading {variation} model: {str(e)}")

    except Exception as e:
        print(f"Error downloading results: {str(e)}")
        print("Automatic download failed. Please use the manual download method.")

    # Print command for manual download
    print("\nTo manually download the results, run the following commands in your terminal:")
    print(f"modal volume get {modal_config.volume_name} {volume_results_path} {local_output_path}")
    print(f"\nTo specifically download the exported models, run:")
    for variation in variations:
        print(f"modal volume get {modal_config.volume_name} {volume_results_path}/exported/{base_config.name}_{variation}.ts {local_output_path}/exported/{base_config.name}_{variation}.ts")

    print(f"\nResults should be available at: {local_output_path}")

if __name__ == "__main__":
    modal.run(main)
