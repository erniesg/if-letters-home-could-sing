import os
import json

class Config:
    def __init__(self):
        self.PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.DATA_DIR = os.path.join(self.PROJECT_DIR, 'data')
        self.PROCESSED_DIR = os.path.join(self.DATA_DIR, 'processed')
        self.COMBINED_DIR = os.path.join(self.PROCESSED_DIR, 'combined')
        self.CHAR_TO_ID_PATH = os.path.join(self.PROCESSED_DIR, 'unified_char_to_id_mapping.json')
        self.ID_TO_CHAR_PATH = os.path.join(self.PROCESSED_DIR, 'unified_id_to_char_mapping.json')

        # Load character mappings
        with open(self.CHAR_TO_ID_PATH, 'r', encoding='utf-8') as f:
            self.char_to_id = json.load(f)
        with open(self.ID_TO_CHAR_PATH, 'r', encoding='utf-8') as f:
            self.id_to_char = json.load(f)

        # Model parameters
        self.INPUT_SIZE = (64, 64)
        self.NUM_CLASSES = len(self.char_to_id)  # Dynamically set based on the mapping

        # Training parameters
        self.BATCH_SIZE = 32
        self.LEARNING_RATE = 0.001
        self.NUM_EPOCHS = 10

        # W&B configuration
        self.WANDB_PROJECT = "if-letters-home-could-sing"
        self.WANDB_ENTITY = "erniesg"

    def update_num_classes(self, num_classes):
        """Update the number of classes based on the sampled dataset"""
        self.NUM_CLASSES = num_classes

    def get_num_classes(self):
        return self.NUM_CLASSES
