from airflow.decorators import dag, task
from airflow.models import Connection
from pendulum import datetime
import os
import json
from modal import Function, Dict
from pathlib import Path

from training_rave.config import RAVEConfig
from src.config import ModalConfig

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": 300,
}

@dag(
    dag_id="rave_training_smoke_test",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["rave", "training"],
)
def rave_training_dag():
    
    @task
    def setup_modal_auth(**context):
        """Set up Modal authentication using Airflow connections"""
        try:
            modal_conn = Connection.get_connection_from_secrets("modal_default")
            extra = json.loads(modal_conn.extra)
            
            os.environ["MODAL_TOKEN_ID"] = extra["token_id"]
            os.environ["MODAL_TOKEN_SECRET"] = extra["token_secret"]
            
            return {"auth_status": "success"}
        except Exception as e:
            raise

    @task
    def initialize_config(**context):
        """Initialize training configuration"""
        try:
            # Use default ModalConfig - all paths and settings will be inherited
            modal_config = ModalConfig()

            # Initialize RAVE config with smoke test parameters
            rave_config = RAVEConfig(
                local_dataset="hainanese_opera",
                name="rave",
                channels=1,
                batch_size=8,
                smoke_test=True,
                progress=True,
                max_steps=1000,
                val_every=100,
                save_every=500,
                modal_config=modal_config  # Pass the modal config with all default settings
            )
            
            return {"rave_config": rave_config.__dict__}
        except Exception as e:
            raise

    @task
    def run_training(config: dict, auth_status: dict, **context):
        """Execute RAVE training using Modal lookup"""
        try:
            # Look up the deployed training function
            train_fn = Function.lookup("rave-training", "train")
            
            # Create RAVEConfig from dict
            rave_config = RAVEConfig(**config["rave_config"])
            
            # Execute training
            result = train_fn.remote(rave_config)
            
            # Get results from shared dict
            results_dict = Dict.from_name("rave-training-results")
            latest_results = results_dict.get("latest_training")
            
            return {
                "modal_result": result,
                "shared_results": latest_results
            }
            
        except Exception as e:
            raise

    # Define task dependencies
    auth_result = setup_modal_auth()
    config = initialize_config()
    training_result = run_training(config, auth_result)

# Instantiate the DAG
rave_training_dag() 