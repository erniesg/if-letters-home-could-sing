import wandb
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_wandb(config):
    """Initialize a new wandb run"""
    try:
        # Convert config to a JSON-serializable dictionary
        config_dict = {k: v for k, v in vars(config).items() if not k.startswith('__')}

        # Handle potential encoding issues
        for key, value in config_dict.items():
            if isinstance(value, dict):
                # For char_to_id and id_to_char mappings
                config_dict[key] = {str(k): str(v) for k, v in value.items()}
            elif isinstance(value, str):
                config_dict[key] = value

        # Remove potentially problematic keys
        config_dict.pop('char_to_id', None)
        config_dict.pop('id_to_char', None)

        logger.debug(f"Config dict: {json.dumps(config_dict, indent=2, ensure_ascii=False)}")

        wandb.init(project=config.WANDB_PROJECT, entity=config.WANDB_ENTITY, config=config_dict)
        return wandb.config
    except Exception as e:
        logger.exception(f"Error initializing wandb: {str(e)}")
        raise

def log_metrics(metrics):
    wandb.log(metrics)

def finish_wandb():
    wandb.finish()
