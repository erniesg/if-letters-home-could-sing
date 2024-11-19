import modal
from pathlib import Path
import os
from .config import ModalConfig
from modal import Mount, Secret, Volume, CloudBucketMount

def create_function(app, config, image, volume, mounts=None, secrets=None):
    """Create a Modal function with the given configuration.
    
    Args:
        app: Modal app instance
        config: ModalConfig instance
        image: Modal image instance
        volume: Modal volume instance
        mounts: Optional dict of mounts to add
        secrets: Optional list of secrets to add
    """
    def decorator(f):
        # Initialize function kwargs
        function_kwargs = {
            "image": image,
            "gpu": config.gpu,
            "cpu": config.cpu_count,
            "memory": config.memory_size,
            "volumes": {config.volume_path: volume},
            "timeout": config.timeout
        }
        
        # Add mounts if provided
        if mounts:
            function_kwargs["mounts"] = mounts
            
        # Add secrets if provided
        if secrets:
            function_kwargs["secrets"] = secrets
            
        return app.function(**function_kwargs)(f)
        
    return decorator

def create_modal_app(config: ModalConfig):
    image = (
        modal.Image.debian_slim(python_version=config.python_version)
        .pip_install(*config.pip_packages)
        .apt_install(*config.apt_packages)
    )
    print(f"Created image with Python {config.python_version}")
    print(f"Installed pip packages: {config.pip_packages}")
    print(f"Installed apt packages: {config.apt_packages}")

    aws_secret = Secret.from_name(config.aws_secret_name)

    app = modal.App(config.app_name, secrets=[aws_secret])
    print(f"Created app '{config.app_name}' with AWS secret '{config.aws_secret_name}'")

    # Create local volume for persistent storage
    local_volume = modal.Volume.from_name(config.volume_name, create_if_missing=True)
    print(f"Created local volume '{config.volume_name}'")

    return app, image, local_volume
