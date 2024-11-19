import subprocess
from pathlib import Path
from typing import List, Any
import modal

def run_command(command):
    try:
        result = subprocess.run(" ".join(command), shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        print(f"Error output: {e.stderr}")

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

def download_from_volume(remote_path: str, local_path: str, volume: modal.Volume):
    local_path = Path(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading from {remote_path} to {local_path}")

    def download_recursive(current_remote_path):
        for file_entry in volume.iterdir(current_remote_path):
            relative_path = Path(file_entry.path).relative_to(remote_path)
            current_local_path = local_path / relative_path

            if file_entry.is_dir():
                current_local_path.mkdir(parents=True, exist_ok=True)
                download_recursive(file_entry.path)
            else:
                current_local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(current_local_path, 'wb') as f:
                    for chunk in volume.read_file(file_entry.path):
                        f.write(chunk)

    download_recursive(remote_path)
    print("Download completed.")

def read_file_from_volume(path: str, volume: modal.Volume) -> str:
    content = b""
    for chunk in volume.read_file(path):
        content += chunk
    return content.decode('utf-8')

def list_files_in_volume(path: str, volume: modal.Volume) -> List[Any]:
    try:
        return volume.listdir(path, recursive=True)
    except Exception as e:
        print(f"Error listing files in {path} from volume: {str(e)}")
        return []
