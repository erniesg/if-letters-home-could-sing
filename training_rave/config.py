from dataclasses import dataclass, field
from typing import List, Optional
from src.config import ModalConfig
import os
from pathlib import Path

@dataclass
class RAVEConfig:
    local_dataset: str
    name: str
    architecture: str = "v2"
    regularization: str = "default"
    channels: int = 1
    lazy: bool = False
    streaming: bool = False
    val_every: int = 250
    epochs: int = 2000  # Changed from max_steps to epochs
    batch_size: int = 8  # Added batch_size
    smoke_test: bool = False
    progress: bool = True
    prior: Optional[str] = None
    additional_args: List[str] = field(default_factory=list)
    modal_config: ModalConfig = field(default_factory=ModalConfig)
    fidelity: Optional[float] = None
    latent_size: Optional[int] = None
    stereo: bool = False
    max_steps: int = 6000000  # Add this line

    @property
    def modal_dataset(self):
        return f"{self.modal_config.volume_path}/input"

    @property
    def modal_save_dir(self):
        return f"{self.modal_config.volume_path}/output"

    @property
    def gcs_dataset_path(self):
        return f"{self.modal_config.gcs_data_path}/{Path(self.local_dataset).name}"

    @property
    def gcs_results_path(self):
        return f"results/{self.name}"

    @property
    def s3_results_path(self):
        return f"output/{self.name}"
