import json

class BaseCharacterMapping:
    def __init__(self):
        self.char_to_id = {}
        self.id_to_char = {}

    def load_initial_mapping(self, char_to_id_path, id_to_char_path):
        with open(char_to_id_path, 'r', encoding='utf-8') as f:
            self.char_to_id = json.load(f)
        with open(id_to_char_path, 'r', encoding='utf-8') as f:
            self.id_to_char = json.load(f)

    def add_character(self, char, id):
        self.char_to_id[char] = id
        self.id_to_char[id] = char

    def get_id(self, char):
        return self.char_to_id.get(char)

    def get_char(self, id):
        return self.id_to_char.get(id)
