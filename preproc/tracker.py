import json
import os

class ProgressTracker:
    def __init__(self, dataset_name, output_dir):
        self.dataset_name = dataset_name
        self.output_dir = output_dir
        self.progress_file = os.path.join(output_dir, f"{dataset_name}_progress.json")
        self.progress = self.load_progress()

    def initialize_progress(self, samples):
        for sample in samples:
            if sample not in self.progress:
                self.progress[sample] = {'status': 'Not Started'}
        self.save_progress()

    def update_progress(self, sample, status):
        if sample not in self.progress:
            self.progress[sample] = {'status': 'Not Started'}
        self.progress[sample]['status'] = status
        self.save_progress()

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f)

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}

    def is_sample_processed(self, sample):
        return self.progress.get(sample, {}).get('status') == 'Completed'

    def get_unprocessed_samples(self, samples):
        return [sample for sample in samples if not self.is_sample_processed(sample)]
