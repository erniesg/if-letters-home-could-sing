import os
import yaml
import multiprocessing
from dotenv import load_dotenv

def load_config():
    load_dotenv()  # This loads the variables from .env

    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Replace ${VAR} placeholders with actual environment variables
    config = replace_env_vars(config)

    # Set optimal num_workers
    config['processing']['num_workers'] = multiprocessing.cpu_count()

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
