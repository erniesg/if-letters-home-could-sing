import cv2
import numpy as np
import logging
import pytesseract
from scipy import ndimage

class ChineseDocumentProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.steps = {
            'resize': self.resize_image,
            'orient': self.correct_orientation,
            'remove_red': self.remove_red_channel,
            'binarize': self.enhanced_binarization,
            'enhance_chars': self.enhance_characters,
            'correct_skew': self.correct_skew,
            'remove_lines': self.remove_lines,
            'detect_content': self.detect_content_area,
            'remove_noise': self.remove_isolated_noise
        }

    def resize_image(self, image: np.ndarray, max_dimension: int) -> np.ndarray:
        self.logger.debug(f"Resizing image to max dimension: {max_dimension}")
        height, width = image.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        return image

    def correct_orientation(self, image: np.ndarray) -> np.ndarray:
        self.logger.debug("Correcting image orientation")
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
                self.logger.warning(f"Tesseract error for angle {angle}")

        return ndimage.rotate(image, best_orientation)

    def remove_red_channel(self, image: np.ndarray) -> np.ndarray:
        self.logger.debug("Removing red channel")
        b, g, _ = cv2.split(image)
        return cv2.merge([b, g, np.zeros_like(b)])

    def enhanced_binarization(self, image: np.ndarray, clip_limit: float, tile_size: int) -> np.ndarray:
        self.logger.debug(f"Binarizing image with clip limit {clip_limit} and tile size {tile_size}")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        equalized = clahe.apply(gray)
        blur = cv2.GaussianBlur(equalized, (5,5), 0)
        return cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

    def enhance_characters(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        self.logger.debug(f"Enhancing characters with kernel size {kernel_size}")
        denoised = cv2.medianBlur(image, 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        strengthened = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        thinned = cv2.ximgproc.thinning(strengthened)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        return clahe.apply(thinned)

    def correct_skew(self, image: np.ndarray) -> np.ndarray:
        self.logger.debug("Correcting skew")
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
        self.logger.debug(f"Removing lines with h_kernel_size {h_kernel_size} and v_kernel_size {v_kernel_size}")
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
        horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        lines = cv2.add(horizontal_lines, vertical_lines)
        return cv2.subtract(image, lines)

    def detect_content_area(self, image: np.ndarray, threshold_factor: float) -> np.ndarray:
        self.logger.debug(f"Detecting content area with threshold factor {threshold_factor}")
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
        self.logger.debug(f"Removing isolated noise with kernel size {kernel_size} and {iterations} iterations")
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=iterations)

    def process(self, image: np.ndarray, steps: list, settings: dict) -> tuple:
        self.logger.info("Starting image processing")
        result = image
        intermediate_results = {}
        for step in steps:
            if step in self.steps:
                self.logger.debug(f"Applying step: {step}")
                result = self.steps[step](result, **settings.get(step, {}))
                intermediate_results[step] = result.copy()
            else:
                self.logger.warning(f"Unknown step: {step}")
        return result, intermediate_results
