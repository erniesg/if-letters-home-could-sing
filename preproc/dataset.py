import random

class DatasetHandler:
    def __init__(self, dataset_name, full_dataset):
        self.dataset_name = dataset_name
        self.full_dataset = full_dataset

    def get_deterministic_sample(self, sample_percentage, seed=42):
        random.seed(seed)
        sample_size = max(1, int(len(self.full_dataset) * sample_percentage))
        return sorted(random.sample(self.full_dataset, sample_size))

    def get_incremental_sample(self, start_percentage, end_percentage, seed=42):
        start_sample = self.get_deterministic_sample(start_percentage, seed)
        end_sample = self.get_deterministic_sample(end_percentage, seed)
        return sorted(set(end_sample) - set(start_sample))
