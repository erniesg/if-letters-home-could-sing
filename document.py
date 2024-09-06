import cv2
import numpy as np
import pytesseract
from scipy import ndimage
from typing import Dict, List, Tuple, Any

class ChineseDocumentProcessor:
    def __init__(self):
        self.steps = {
            'resize': {
                'func': self.resize_image,
                'settings': {
                    'max_dimension': {'value': 2000, 'type': 'int', 'range': (500, 5000)}
                }
            },
            'orient': {
                'func': self.correct_orientation,
                'settings': {}  # No adjustable settings for this step
            },
            'remove_red': {
                'func': self.remove_red_channel,
                'settings': {}  # No adjustable settings for this step
            },
            'binarize': {
                'func': self.enhanced_binarization,
                'settings': {
                    'clip_limit': {'value': 2.0, 'type': 'float', 'range': (0.5, 5.0)},
                    'tile_size': {'value': 8, 'type': 'int', 'range': (4, 16)}
                }
            },
            'enhance_chars': {
                'func': self.enhance_characters,
                'settings': {
                    'kernel_size': {'value': 2, 'type': 'int', 'range': (1, 5)}
                }
            },
            'correct_skew': {
                'func': self.correct_skew,
                'settings': {}  # No adjustable settings for this step
            },
            'remove_lines': {
                'func': self.remove_lines,
                'settings': {
                    'h_kernel_size': {'value': 40, 'type': 'int', 'range': (10, 100)},
                    'v_kernel_size': {'value': 40, 'type': 'int', 'range': (10, 100)}
                }
            },
            'detect_content': {
                'func': self.detect_content_area,
                'settings': {
                    'threshold_factor': {'value': 0.5, 'type': 'float', 'range': (0.1, 1.0)}
                }
            },
            'remove_noise': {
                'func': self.remove_isolated_noise,
                'settings': {
                    'kernel_size': {'value': 3, 'type': 'int', 'range': (1, 7)},
                    'iterations': {'value': 2, 'type': 'int', 'range': (1, 5)}
                }
            }
        }

    def resize_image(self, image: np.ndarray, max_dimension: int) -> np.ndarray:
        height, width = image.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        return image

    def correct_orientation(self, image: np.ndarray) -> np.ndarray:
        orientations = [0, 90, 180, 270]
        max_confidence = 0
        best_orientation = 0

        for angle in orientations:
            rotated = ndimage.rotate(image, angle)
            gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)

            try:
                osd = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.DICT)
                confidence = float(osd['orientation_conf'])
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_orientation = angle
            except pytesseract.TesseractError:
                print(f"Tesseract error for angle {angle}")

        return ndimage.rotate(image, best_orientation)

    def remove_red_channel(self, image: np.ndarray) -> np.ndarray:
        b, g, _ = cv2.split(image)
        return cv2.merge([b, g, np.zeros_like(b)])

    def enhanced_binarization(self, image: np.ndarray, clip_limit: float, tile_size: int) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        equalized = clahe.apply(gray)
        blur = cv2.GaussianBlur(equalized, (5,5), 0)
        return cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

    def enhance_characters(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        denoised = cv2.medianBlur(image, 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        strengthened = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        thinned = cv2.ximgproc.thinning(strengthened)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        return clahe.apply(thinned)

    def correct_skew(self, image: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def remove_lines(self, image: np.ndarray, h_kernel_size: int, v_kernel_size: int) -> np.ndarray:
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
        horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        lines = cv2.add(horizontal_lines, vertical_lines)
        return cv2.subtract(image, lines)

    def detect_content_area(self, image: np.ndarray, threshold_factor: float) -> np.ndarray:
        vertical_profile = np.sum(image, axis=1)
        horizontal_profile = np.sum(image, axis=0)
        v_threshold = np.mean(vertical_profile) * threshold_factor
        h_threshold = np.mean(horizontal_profile) * threshold_factor
        v_start = np.argmax(vertical_profile > v_threshold)
        v_end = len(vertical_profile) - np.argmax(vertical_profile[::-1] > v_threshold)
        h_start = np.argmax(horizontal_profile > h_threshold)
        h_end = len(horizontal_profile) - np.argmax(horizontal_profile[::-1] > h_threshold)
        return image[v_start:v_end, h_start:h_end]

    def remove_isolated_noise(self, image: np.ndarray, kernel_size: int, iterations: int) -> np.ndarray:
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=iterations)

    def process(self, image: np.ndarray, steps: List[str], settings: Dict[str, Dict[str, Any]]) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        result = image
        intermediate_results = {}

        for step in steps:
            if step in self.steps:
                step_function = self.steps[step]['func']
                if self.steps[step]['settings']:
                    step_settings = {k: v for k, v in settings.get(step, {}).items()}
                    result = step_function(result, **step_settings)
                else:
                    result = step_function(result)
                intermediate_results[step] = result.copy()
            else:
                print(f"Warning: Unknown step '{step}' skipped.")

        return result, intermediate_results
