from .config import RAVEConfig
from typing import List
from pathlib import Path
import os

def get_preprocess_command(config: RAVEConfig, input_path: Path, output_path: Path) -> List[str]:
    cmd = [
        "rave", "preprocess",
        "--input_path", str(input_path),
        "--output_path", str(output_path / "preprocessed"),
        "--channels", str(config.channels)
    ]
    if config.lazy:
        cmd.append("--lazy")
    return cmd

def get_train_command(config: RAVEConfig, output_path: Path, max_steps: int, val_every: int) -> List[str]:
    cmd = [
        "rave", "train",
        "--config", config.architecture,
        "--db_path", str(output_path / "preprocessed"),
        "--name", config.name,
        "--out_path", str(output_path / "models"),
        "--channels", str(config.channels),
        "--val_every", str(val_every or config.val_every),
        "--max_steps", str(max_steps or config.max_steps),
        "--batch", str(config.batch_size)
    ]

    if config.lazy:
        cmd.append("--lazy")
    if config.streaming:
        cmd.append("--streaming")
    if config.smoke_test:
        cmd.append("--smoke_test")
    if config.progress:
        cmd.append("--progress")

    # Check for existing checkpoints
    checkpoints_path = output_path / "models" / config.name / "checkpoints"
    if checkpoints_path.exists():
        latest_checkpoint = max(checkpoints_path.glob("*.ckpt"), key=os.path.getctime, default=None)
        if latest_checkpoint:
            print(f"Found latest checkpoint: {latest_checkpoint}")
            cmd.extend(["--ckpt", str(latest_checkpoint)])

    return cmd

def get_export_command(config: RAVEConfig, output_path: Path, variation_name: str = None) -> List[str]:
    # Find the directory containing config.gin
    models_path = output_path / "models"
    run_id_dir = None
    for dir_name in os.listdir(models_path):
        if dir_name.startswith(config.name):
            potential_run_dir = models_path / dir_name
            if (potential_run_dir / "config.gin").exists():
                run_id_dir = potential_run_dir
                break

    if run_id_dir is None:
        raise FileNotFoundError(f"Could not find config.gin in any run directory under {models_path}")

    cmd = [
        "rave", "export",
        "--run", str(run_id_dir),
        "--name", variation_name or config.name,
        "--output", str(output_path / "exported"),
        "--channels", str(config.channels),
    ]

    if config.streaming:
        cmd.append("--streaming")

    if config.fidelity is not None:
        cmd.extend(["--fidelity", str(config.fidelity)])
    elif config.latent_size is not None:
        cmd.extend(["--latent_size", str(config.latent_size)])

    return cmd

def get_train_prior_command(config: RAVEConfig) -> List[str]:
    cmd = [
        "rave", "train_prior",
        "--model", f"{config.modal_save_dir}/models",
        "--db_path", f"{config.modal_save_dir}/preprocessed",
        "--out_path", f"{config.modal_save_dir}/priors"
    ]
    cmd.extend(config.additional_args)
    return cmd
