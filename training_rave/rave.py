from .config import RAVEConfig
from typing import List
from pathlib import Path

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

def get_train_command(config: RAVEConfig, output_path: Path) -> List[str]:
    cmd = [
        "rave", "train",
        "--config", config.architecture,
        "--db_path", str(output_path / "preprocessed"),
        "--name", config.name,
        "--out_path", str(output_path / "models"),
        "--channels", str(config.channels),
        "--val_every", str(config.val_every),
        "--max_steps", str(config.max_steps)
    ]
    if config.regularization != "default":
        cmd.extend(["--config", config.regularization])
    if config.smoke_test:
        cmd.append("--smoke_test")
    if not config.progress:
        cmd.append("--no-progress")
    cmd.extend(config.additional_args)
    return cmd

def get_export_command(config: RAVEConfig) -> List[str]:
    cmd = [
        "rave", "export",
        "--run", f"{config.modal_save_dir}/models",
        "--name", config.name
    ]
    if config.streaming:
        cmd.append("--streaming")
    if config.prior:
        cmd.extend(["--prior", config.prior])
    cmd.extend(config.additional_args)
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
