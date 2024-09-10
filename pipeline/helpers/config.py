import os
import yaml
import multiprocessing
from dotenv import load_dotenv

def get_config():
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to the root directory (two levels up from helpers)
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))

    # Load .env file from the root directory
    dotenv_path = os.path.join(root_dir, '.env')
    load_dotenv(dotenv_path)

    # Construct the path to settings.yaml
    settings_path = os.path.join(root_dir, 'pipeline', 'config', 'settings.yaml')

    with open(settings_path, 'r') as f:
        config = yaml.safe_load(f)

    # Replace ${VAR} placeholders with actual environment variables
    config = replace_env_vars(config)

    return config

def replace_env_vars(obj):
    if isinstance(obj, dict):
        return {k: replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_env_vars(elem) for elem in obj]
    elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
        env_var = obj[2:-1]
        return os.getenv(env_var, obj)
    else:
        return obj
