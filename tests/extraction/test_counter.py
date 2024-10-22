import unittest
import os
import json
from preproc.counter import Counter

class TestCounter(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_counter'
        os.makedirs(self.test_dir, exist_ok=True)
        self.counter = Counter('test_dataset', self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)

    def test_initialization(self):
        # Test empty initialization
        self.assertEqual(self.counter.counters, {})

        # Test loading existing counters
        existing_counters = {'00001': 5, '00002': 3}
        with open(os.path.join(self.test_dir, 'test_dataset_counters.json'), 'w') as f:
            json.dump(existing_counters, f)

        new_counter = Counter('test_dataset', self.test_dir)
        self.assertEqual(new_counter.counters, existing_counters)

    def test_get_next_counter(self):
        # Test getting counter for new character ID
        self.assertEqual(self.counter.get_next_counter('00001'), 1)

        # Test getting counter for existing character ID
        self.assertEqual(self.counter.get_next_counter('00001'), 2)
        self.assertEqual(self.counter.get_next_counter('00002'), 1)
        self.assertEqual(self.counter.get_next_counter('00001'), 3)

    def test_save_and_load(self):
        self.counter.get_next_counter('00001')
        self.counter.get_next_counter('00002')
        self.counter.save_counters()

        # Verify file content
        with open(os.path.join(self.test_dir, 'test_dataset_counters.json'), 'r') as f:
            saved_counters = json.load(f)
        self.assertEqual(saved_counters, {'00001': 1, '00002': 1})

        # Load counters in a new instance
        new_counter = Counter('test_dataset', self.test_dir)
        self.assertEqual(new_counter.counters, {'00001': 1, '00002': 1})

    def test_multiple_characters(self):
        for i in range(1, 6):
            char_id = f'{i:05d}'
            for _ in range(i):
                self.counter.get_next_counter(char_id)

        expected = {f'{i:05d}': i for i in range(1, 6)}
        self.assertEqual(self.counter.counters, expected)

    def test_persistence_across_instances(self):
        self.counter.get_next_counter('00001')
        self.counter.save_counters()

        counter2 = Counter('test_dataset', self.test_dir)
        self.assertEqual(counter2.get_next_counter('00001'), 2)

    def test_reset_counters(self):
        self.counter.get_next_counter('00001')
        self.counter.get_next_counter('00002')
        self.counter.reset_counters()
        self.assertEqual(self.counter.counters, {})

        # Ensure reset is persisted
        self.counter.save_counters()
        new_counter = Counter('test_dataset', self.test_dir)
        self.assertEqual(new_counter.counters, {})

    def test_get_filename(self):
        filename1 = self.counter.get_filename('00001')
        self.assertEqual(filename1, 'test_dataset_00001_1.png')

        filename2 = self.counter.get_filename('00001')
        self.assertEqual(filename2, 'test_dataset_00001_2.png')

        filename3 = self.counter.get_filename('00002')
        self.assertEqual(filename3, 'test_dataset_00002_1.png')

    def test_thread_safety(self):
        import threading

        def update_counter(char_id, num_updates):
            for _ in range(num_updates):
                self.counter.get_next_counter(char_id)

        threads = []
        for i in range(10):
            char_id = f'{i:05d}'
            t = threading.Thread(target=update_counter, args=(char_id, 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for i in range(10):
            char_id = f'{i:05d}'
            self.assertEqual(self.counter.counters[char_id], 100)

if __name__ == '__main__':
    unittest.main()
