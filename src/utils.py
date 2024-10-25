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

    except Exception as e:
        print(f"Error during upload: {str(e)}")
        raise

    # Count files and get sizes after upload
    file_count = 0
    total_size = 0
    file_types = {}

    for root, _, files in os.walk(local_path):
        for file in files:
            file_path = Path(root) / file
            file_count += 1
            file_size = file_path.stat().st_size
            total_size += file_size
            file_type = file_path.suffix.lower()
            file_types[file_type] = file_types.get(file_type, 0) + 1

    print(f"Upload completed. Total files uploaded: {file_count}")
    print(f"Total size uploaded: {total_size / (1024 * 1024):.2f} MB")
    print("File types summary:")
    for file_type, count in file_types.items():
        print(f"  {file_type}: {count} files")

    return file_count, total_size, file_types

def run_command(command):
    """
    Run a shell command and print its output in real-time.
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )

    for line in iter(process.stdout.readline, ''):
        print(line, end='')

    process.stdout.close()
    return_code = process.wait()

    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

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
