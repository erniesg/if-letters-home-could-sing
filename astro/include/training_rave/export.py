import modal
from pathlib import Path
import sys

# Add the parent directory to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from src.config import ModalConfig
from src.app import create_modal_app, create_function
from training_rave.config import RAVEConfig
from training_rave.rave import get_export_command
from src.utils import run_command

# Initialize ModalConfig
modal_config = ModalConfig()

# Create Modal app, image, and volume
app, image, volume = create_modal_app(modal_config)

@create_function(app, modal_config, image, volume)
def export_checkpoint(config: RAVEConfig, checkpoint_path: str, version: str):
    output_path = Path(config.modal_config.volume_path) / "output/rave"

    # Get the model's root directory (where config.gin is located)
    model_root = Path(config.modal_config.volume_path) / f"output/rave/models/{config.name}_e18d54798e"
    checkpoint_dir = model_root / f"version_{version}"

    print(f"Model root directory: {model_root}")
    print(f"Checkpoint directory: {checkpoint_dir}")
    print(f"Directory contents: {list(model_root.glob('*'))}")

    variations = [
        {"channels": 1, "streaming": False},
        {"channels": 1, "streaming": True},
    ]

    results = []
    for variation in variations:
        variation_config = RAVEConfig(**{**config.__dict__, **variation})
        variation_name = f"{config.name}_v{version}_ch{variation['channels']}_{'streaming' if variation['streaming'] else 'non_streaming'}"

        # Pass the model root directory as the run directory (where config.gin is)
        export_command = get_export_command(
            variation_config,
            output_path,
            variation_name
        )

        # Override the --run parameter with the model root directory
        run_index = export_command.index("--run") + 1
        export_command[run_index] = str(model_root)

        print(f"Export command for {variation_name}: {' '.join(export_command)}")
        run_command(export_command)
        results.append(f"Exported {variation_name}")

    return results

@app.local_entrypoint()
def main(
    model_id: str = "rave_e18d54798e",
    versions: str = "15,16,17",
    name: str = "rave",
    fidelity: float = 0.999,
):
    base_config = RAVEConfig(
        name=name,
        modal_config=modal_config,
        fidelity=fidelity,
        local_dataset="dummy",
        channels=1,
        lazy=False,
        streaming=False,
        epochs=2000,
        batch_size=8,
        smoke_test=False,
        progress=True
    )

    version_list = versions.split(',')

    for version in version_list:
        checkpoint_path = f"output/rave/models/{model_id}/version_{version}/checkpoints/best.ckpt"
        print(f"Exporting version {version} from checkpoint: {checkpoint_path}")
        results = export_checkpoint.remote(base_config, checkpoint_path, version)
        print(f"Results for version {version}:")
        for result in results:
            print(f"  {result}")

if __name__ == "__main__":
    modal.run(main)
