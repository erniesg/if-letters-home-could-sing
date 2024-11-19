import modal
from pathlib import Path
import os
from .config import ModalConfig
from modal import Mount, Secret, Volume, CloudBucketMount

def create_function(app: modal.App, config: ModalConfig, image: modal.Image, local_volume: modal.Volume):
    print(f"Local src path: {config.local_src_path}")
    print(f"Remote src path: {config.remote_src_path}")

    mounts = [
        modal.Mount.from_local_dir(config.local_src_path, remote_path=config.remote_src_path)
    ]

    print(f"Created mount from {config.local_src_path} to {config.remote_src_path}")

    s3_mount = modal.CloudBucketMount(
        config.s3_bucket_name,
        secret=modal.Secret.from_name(config.aws_secret_name)
    )

    def wrapper(func):
        function_kwargs = {
            "image": image,
            "gpu": config.gpu,
            "mounts": mounts,
            "volumes": {
                config.volume_path: local_volume,
                config.s3_mount_path: s3_mount
            },
            "secret": modal.Secret.from_name(config.aws_secret_name),
            "timeout": config.timeout
        }

        # Add optional resource configurations
        if config.cpu_count is not None:
            function_kwargs["cpu"] = config.cpu_count
        if config.memory_size is not None:
            function_kwargs["memory"] = config.memory_size
        if config.disk_size is not None:
            function_kwargs["ephemeral_disk"] = config.disk_size

        wrapped_func = app.function(**function_kwargs)(func)

        print(f"Created function with:")
        print(f"- GPU: {config.gpu}")
        print(f"- CPU cores: {config.cpu_count}")
        print(f"- Memory: {config.memory_size} MB")
        print(f"- Disk: {config.disk_size} MB")
        print(f"- Local volume mounted at: {config.volume_path}")
        print(f"- S3 bucket mounted at: {config.s3_mount_path}")
        print(f"- Function timeout: {config.timeout} seconds")

        return wrapped_func

    return wrapper

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
