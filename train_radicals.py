import sys
import os
import argparse
import modal
from modal import Image, Mount, Volume

print(f"Python version: {sys.version}")

# Define the CUDA-enabled image
cuda_version = "12.4.0"
flavor = "devel"
os_version = "ubuntu22.04"
tag = f"{cuda_version}-{flavor}-{os_version}"

print(f"Using CUDA image: nvidia/cuda:{tag}")

image = (
    modal.Image.from_registry(f"nvidia/cuda:{tag}", add_python="3.11")
    .apt_install("git")
    .pip_install(
        "torch",
        "torchvision",
        "matplotlib",
        "numpy",
        "pillow",
        "google-auth",
        "google-cloud-storage",
        "tqdm",
        "opencv-python-headless",
        "scikit-image",
        "transformers",
        "timm",
        "einops",
        "hydra-core"
    )
    .run_commands("pip install git+https://github.com/facebookresearch/segment-anything.git")
)

# Define mount paths
DATASET_MOUNT_PATH = "/data"
MOCO_MODEL_MOUNT_PATH = "/moco_model"

# Create volumes
dataset_volume = Volume.from_name("chinese-dataset-volume", create_if_missing=True)
moco_model_volume = Volume.from_name("moco-model-volume", create_if_missing=True)

# Mount local script files
local_mounts = [
    Mount.from_local_file("preproc_train.py", remote_path="/app/preproc_train.py"),
    Mount.from_local_file("radicals.py", remote_path="/app/radicals.py"),
]

# Mount the service account key file
credentials_mount = Mount.from_local_file(
    "/Users/erniesg/code/erniesg/if_letters_home_could_sing/dev/iflettershomecouldsing-5287b296bb69.json",
    remote_path="/secrets/google-credentials.json"
)

# Define the app with default image and mounts
app = modal.App(
    image=image,
    mounts=local_mounts + [credentials_mount],
    volumes={
        DATASET_MOUNT_PATH: dataset_volume,
        MOCO_MODEL_MOUNT_PATH: moco_model_volume,
    }
)

@app.function()
def validate_cuda():
    import subprocess
    try:
        output = subprocess.check_output(["nvidia-smi"], text=True)
        print("CUDA is available:")
        print(output)
        return True
    except subprocess.CalledProcessError:
        print("CUDA is not available")
        return False

@app.function()
def count_files_in_volume():
    dataset_path = f"{DATASET_MOUNT_PATH}/data/Puzzle-Pieces-Picker Dataset/Dataset"
    try:
        total_files = sum(1 for _ in dataset_volume.listdir(dataset_path, recursive=True))
        return total_files
    except Exception as e:
        print(f"Error counting files: {e}")
        return 0

@app.function(timeout=600)
def get_blob_batches():
    from google.oauth2 import service_account
    from google.cloud import storage

    print("Fetching blob list...")
    SERVICE_ACCOUNT_FILE = '/secrets/google-credentials.json'
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    client = storage.Client(credentials=credentials)
    bucket = client.get_bucket("ifletters")

    blobs = list(bucket.list_blobs(prefix="data/Puzzle-Pieces-Picker Dataset/"))
    total_files = len(blobs)
    print(f"Found {total_files} files in the bucket.")

    if total_files < 351898:
        print(f"Warning: Expected at least 351,898 files in the bucket, but found {total_files}.")

    blob_names = [blob.name for blob in blobs]
    batch_size = 1000
    blob_name_batches = [blob_names[i:i + batch_size] for i in range(0, len(blob_names), batch_size)]

    return blob_name_batches

@app.function(timeout=1800)
def download_blob_batch(blob_names):
    import io
    from google.oauth2 import service_account
    from google.cloud import storage

    SERVICE_ACCOUNT_FILE = '/secrets/google-credentials.json'
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    client = storage.Client(credentials=credentials)
    bucket = client.get_bucket("ifletters")

    results = []
    for blob_name in blob_names:
        destination_path = f"{DATASET_MOUNT_PATH}/{blob_name}"

        # Check if file exists before attempting to download
        if destination_path in dataset_volume.listdir("", recursive=True):
            results.append(f"Skipped existing file: {blob_name}")
            continue

        try:
            blob = bucket.blob(blob_name)
            with dataset_volume.batch_upload() as batch:
                batch.put_file(io.BytesIO(blob.download_as_bytes()), destination_path)
            results.append(f"Downloaded: {blob_name}")
        except Exception as e:
            results.append(f"Error downloading {blob_name}: {str(e)}")

    return results

@app.function(timeout=3600)
def check_and_download_dataset():
    print("Checking dataset in volume...")
    file_count = count_files_in_volume.remote()
    print(f"Found {file_count} files in the volume.")

    if file_count >= 351898:
        print("Dataset is complete. Skipping download.")
        return True

    print("Dataset is incomplete. Starting download process...")

    blob_name_batches = get_blob_batches.remote()
    print(f"Starting parallel download of {len(blob_name_batches)} batches...")

    all_results = list(download_blob_batch.map(blob_name_batches, return_exceptions=True))

    # Process results
    results = []
    for batch_result in all_results:
        if isinstance(batch_result, Exception):
            print(f"Error processing batch: {str(batch_result)}")
        else:
            results.extend(batch_result)

    success_count = sum(1 for result in results if result.startswith("Downloaded"))
    skip_count = sum(1 for result in results if result.startswith("Skipped"))
    error_count = sum(1 for result in results if result.startswith("Error"))

    print(f"Download completed. Successfully downloaded: {success_count}, Skipped: {skip_count}, Errors: {error_count}")

    dataset_volume.commit()

    final_count = count_files_in_volume.remote()
    print(f"Final file count in volume: {final_count}")
    return final_count >= 351898

@app.function(timeout=1800)
def load_dataset():
    print("Starting dataset loading function...")
    sys.path.append("/app")
    from preproc_train import get_dataloader

    dataset_volume.reload()

    if not check_and_download_dataset.remote():
        raise ValueError("Failed to download or verify the complete dataset.")

    print("Loading dataset...")
    dataloader = get_dataloader(f"{DATASET_MOUNT_PATH}/data/Puzzle-Pieces-Picker Dataset/Dataset")
    print("Dataset loaded.")

    return dataloader

@app.function(gpu="any", timeout=1800)
def train_and_visualize(dataloader):
    import torch
    import matplotlib.pyplot as plt
    from io import BytesIO
    import base64

    print("Starting training and visualization function...")
    sys.path.append("/app")
    from radicals import RadicalSegmentor, MoCoAnnotator, run_segmentation_and_annotation
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    if not validate_cuda.remote():
        raise RuntimeError("CUDA is not available in the runtime environment")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")

    moco_model_path = f"{MOCO_MODEL_MOUNT_PATH}/moco_model.pth"
    moco_model_volume.reload()

    print("Initializing models...")
    segmentor = RadicalSegmentor()
    annotator = MoCoAnnotator(moco_model_path)
    print("Models initialized.")

    for images, _ in dataloader:
        print(f"Processing batch of {len(images)} images...")
        for img in images:
            img = img.to(device)
            if img.dim() == 3:
                img = img.unsqueeze(0)

            print("Running segmentation and annotation...")
            annotations, masks = run_segmentation_and_annotation(img, segmentor, annotator)
            print(f"Generated {len(masks)} masks.")

            fig, axs = plt.subplots(1, len(masks), figsize=(10, 10))
            for i, mask in enumerate(masks):
                mask_np = mask.squeeze().cpu().numpy()
                axs[i].imshow(mask_np, cmap='gray')
                axs[i].set_title(f"Mask {i+1}")

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close(fig)

            print("Saving MoCo model...")
            torch.save(annotator.moco_model.state_dict(), moco_model_path)
            moco_model_volume.commit()
            print("MoCo model saved.")

            print("Processing completed.")
            return {
                'annotations': annotations,
                'visualization': image_base64
            }

def main(mode='local'):
    print(f"Running in {mode} mode")

    if mode == 'local':
        from radicals import get_device, RadicalSegmentor, MoCoAnnotator, run_segmentation_and_annotation
        from preproc_train import get_dataloader
        import torch
        import matplotlib.pyplot as plt

        device = get_device()
        print(f"Using device: {device}")

        dataset_path = 'data/Puzzle-Pieces-Picker Dataset'
        moco_model_path = 'models/moco_model.pth'

        print("Loading dataset...")
        dataloader = get_dataloader(dataset_path)
        print("Dataset loaded.")

        print("Initializing models...")
        segmentor = RadicalSegmentor()
        annotator = MoCoAnnotator(moco_model_path)
        print("Models initialized.")

        for images, _ in dataloader:
            for img in images:
                img = img.to(device)
                if img.dim() == 3:
                    img = img.unsqueeze(0)

                print("Running segmentation and annotation...")
                annotations, masks = run_segmentation_and_annotation(img, segmentor, annotator)
                print(f"Generated {len(masks)} masks.")

                plt.figure(figsize=(10, 10))
                for i, mask in enumerate(masks):
                    plt.subplot(1, len(masks), i+1)
                    mask_np = mask.squeeze().cpu().numpy()
                    plt.imshow(mask_np, cmap='gray')
                    plt.title(f"Mask {i+1}")
                plt.show()

                print("Saving MoCo model...")
                annotator.save_model(moco_model_path)
                print("MoCo model saved.")

                break
            break
    else:  # Modal mode
        import base64
        print("Starting Modal run...")
        with app.run():
            dataloader = load_dataset.remote()
            result = train_and_visualize.remote(dataloader)
        print("Modal run completed.")
        print(f"Annotations: {result['annotations']}")
        with open("visualization.png", "wb") as f:
            f.write(base64.b64decode(result['visualization']))
        print("Visualization saved as visualization.png")

@app.local_entrypoint()
def cli():
    parser = argparse.ArgumentParser(description="Train and visualize Chinese character recognition")
    parser.add_argument('--mode', choices=['local', 'modal'], default='local', help="Run mode: local or modal")
    args = parser.parse_args()
    main(mode=args.mode)

if __name__ == "__main__":
    cli()
