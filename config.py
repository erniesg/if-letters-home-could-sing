from typing import Dict, List, Any

class ConfigManager:
    DEFAULT_SETTINGS = {
        "resize": {
            "max_dimension": {"value": 2000, "type": "int", "range": (500, 5000)}
        },
        "binarize": {
            "clip_limit": {"value": 2.0, "type": "float", "range": (0.5, 5.0)},
            "tile_size": {"value": 8, "type": "int", "range": (4, 16)}
        },
        "enhance_chars": {
            "kernel_size": {"value": 2, "type": "int", "range": (1, 5)}
        },
        "remove_lines": {
            "h_kernel_size": {"value": 40, "type": "int", "range": (10, 100)},
            "v_kernel_size": {"value": 40, "type": "int", "range": (10, 100)}
        },
        "detect_content": {
            "threshold_factor": {"value": 0.5, "type": "float", "range": (0.1, 1.0)}
        },
        "remove_noise": {
            "kernel_size": {"value": 3, "type": "int", "range": (1, 7)},
            "iterations": {"value": 2, "type": "int", "range": (1, 5)}
        }
    }

    def __init__(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.steps = []

    def update_step(self, step: str, value: bool):
        if value and step not in self.steps:
            self.steps.append(step)
        elif not value and step in self.steps:
            self.steps.remove(step)

    def update_setting(self, step: str, setting: str, value: Any):
        if step in self.settings and setting in self.settings[step]:
            self.settings[step][setting]["value"] = value

    def get_steps(self) -> List[str]:
        return self.steps

    def get_settings(self) -> Dict[str, Dict[str, Any]]:
        return {step: {k: v["value"] for k, v in settings.items()} for step, settings in self.settings.items()}

    def get_setting_details(self) -> Dict[str, Dict[str, Any]]:
        return self.settings

    def reset_to_defaults(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.steps = []
