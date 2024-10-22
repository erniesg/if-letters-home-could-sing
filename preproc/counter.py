import os
import json
from threading import Lock

class Counter:
    def __init__(self, dataset_name, progress_dir):
        self.dataset_name = dataset_name
        self.progress_dir = progress_dir
        self.counter_file = os.path.join(self.progress_dir, f'{self.dataset_name}_counters.json')
        self.counters = self.load_counters()
        self.lock = Lock()

    def load_counters(self):
        if os.path.exists(self.counter_file):
            with open(self.counter_file, 'r') as f:
                return json.load(f)
        return {}

    def save_counters(self):
        os.makedirs(os.path.dirname(self.counter_file), exist_ok=True)
        with open(self.counter_file, 'w') as f:
            json.dump(self.counters, f)

    def get_next_counter(self, char_id):
        with self.lock:
            self.counters[char_id] = self.counters.get(char_id, 0) + 1
            self.save_counters()  # Add this line
            return self.counters[char_id]

    def reset_counters(self):
        with self.lock:
            self.counters = {}
            self.save_counters()

    def get_filename(self, char_id):
        counter = self.get_next_counter(char_id)
        return f"{self.dataset_name}_{char_id}_{counter}.png"
