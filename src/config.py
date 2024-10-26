from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ModalConfig:
    app_name: str = "if-letters-home-could-sing"
    volume_name: Optional[str] = None
    volume_path: str = "/data"
    remote_project_path: str = "/root/project"
    remote_src_path: str = "/root/src"
    local_project_root: str = "."
    local_src_path: str = "src"
    python_version: str = "3.10"
    pip_packages: List[str] = field(default_factory=lambda: [
        "torch",
        "tensorboard",
        "acids-rave",
        "torchaudio",
        "boto3"  # Add this for GCS support
    ])
    apt_packages: List[str] = field(default_factory=lambda: ["ffmpeg"])
    gpu: str = "any"
    timeout: int = 10800  # 3 hours in seconds
    gcs_secret_name: str = "gcp-secret"
    gcs_bucket_name: str = "if-letters-home-could-sing"
    gcs_data_path: str = "data"  # Add this line
    aws_secret_name: str = "aws-secret"
    s3_bucket_name: str = "if-letters-home-could-sing"
    s3_data_path: str = "data/hainanese_opera"
    s3_mount_path: str = "/s3-data"  # Add this line

    def __post_init__(self):
        if self.volume_name is None:
            self.volume_name = self.app_name
