import os
from pathlib import Path
import modal
import subprocess

def upload_to_volume(local_path: str, remote_path: str, volume: modal.Volume):
    print(f"Starting upload_to_volume function")
    local_path = Path(local_path)
    if not local_path.exists():
        print(f"Local path {local_path} does not exist.")
        return

    print(f"Uploading from {local_path} to {remote_path}")

    try:
        with volume.batch_upload(force=True) as batch:
            batch.put_directory(str(local_path), remote_path)
            print(f"Directory {local_path} uploaded to {remote_path}")

        print("Batch upload completed")
        volume.commit()  # Ensure changes are persisted

    except Exception as e:
        print(f"Error during upload: {str(e)}")
        raise

def run_command(command):
    try:
        result = subprocess.run(" ".join(command), shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        print(f"Error output: {e.stderr}")

def download_from_volume(remote_path: str, local_path: str, volume: modal.Volume):
    local_path = Path(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading from {remote_path} to {local_path}")
    for file_entry in volume.iterdir(remote_path):
        local_file_path = local_path / file_entry.name
        with open(local_file_path, 'wb') as f:
            for chunk in volume.read_file(file_entry.path):
                f.write(chunk)

    print("Download completed.")
