import os
import modal
from modal import Image, Secret, Volume, Mount
import torch
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = modal.App(name="chinese-char-recognition")

# Create volumes
dataset_volume = Volume.from_name("chinese-dataset-volume", create_if_missing=True)
moco_model_volume = Volume.from_name("moco-model-volume", create_if_missing=True)

# Define mount paths
DATASET_MOUNT_PATH = "/data"
MOCO_MODEL_MOUNT_PATH = "/moco_model"

# Mount local script files
local_mounts = [
    Mount.from_local_file("preproc_train.py", remote_path="/app/preproc_train.py"),
    Mount.from_local_file("radicals.py", remote_path="/app/radicals.py"),
]

def download_dataset():
    result = os.system(f"gsutil -m cp -r gs://ifletters/data/Puzzle-Pieces-Picker\ Dataset/ {DATASET_MOUNT_PATH}")
    if result != 0:
        raise Exception("Failed to download dataset")

def install_sam2():
    import subprocess
    subprocess.run(["git", "clone", "https://github.com/facebookresearch/segment-anything-2.git"], check=True)
    subprocess.run(["pip", "install", "-e", "./segment-anything-2"], check=True)

def download_sam2_model():
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large")

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install("torch", "torchvision", "matplotlib", "numpy", "pillow", "google-cloud-storage", "transformers")
    .run_function(install_sam2)
    .run_function(download_sam2_model)
    .run_function(download_dataset)
)

@app.function(
    image=image,
    gpu="A100",
    secret=Secret.from_name("my-google-secret"),
    volumes={
        DATASET_MOUNT_PATH: dataset_volume,
        MOCO_MODEL_MOUNT_PATH: moco_model_volume
    },
    mounts=local_mounts
)
def train_and_visualize():
    import sys
    sys.path.append("/app")
    from preproc_train import get_dataloader
    from radicals import RadicalSegmentor, MoCoAnnotator, run_segmentation_and_annotation

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    dataloader = get_dataloader(DATASET_MOUNT_PATH)
    moco_model_path = f"{MOCO_MODEL_MOUNT_PATH}/moco_model.pth"

    segmentor = RadicalSegmentor()
    annotator = MoCoAnnotator(moco_model_path)

    for images, _ in dataloader:
        for img in images:
            img = img.to(device)
            if img.dim() == 3:
                img = img.unsqueeze(0)

            annotations, masks = run_segmentation_and_annotation(img, segmentor, annotator)

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

            torch.save(annotator.moco_model.state_dict(), moco_model_path)
            moco_model_volume.commit()

            return {
                'annotations': annotations,
                'visualization': image_base64
            }

@app.local_entrypoint()
def main():
    result = train_and_visualize.remote()

    print(f"Annotations: {result['annotations']}")
    with open("visualization.png", "wb") as f:
        f.write(base64.b64decode(result['visualization']))
    print("Visualization saved as visualization.png")

if __name__ == "__main__":
    main()
