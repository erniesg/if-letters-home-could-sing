import cv2
import numpy as np
from typing import List, Tuple, Dict
import argparse
from scipy import ndimage
import pytesseract

def remove_lines(image: np.ndarray) -> np.ndarray:
    # Create the horizontal kernel
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))

    # Create the vertical kernel
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

    # Detect horizontal lines
    horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Detect vertical lines
    vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Combine the lines
    lines = cv2.add(horizontal_lines, vertical_lines)

    # Remove the lines from the original image
    result = cv2.subtract(image, lines)

    return result

import cv2
import numpy as np
from typing import List, Tuple, Dict
from scipy import ndimage
import pytesseract

def enhance_characters(binary_image):
    # Noise reduction
    denoised = cv2.medianBlur(binary_image, 3)

    # Morphological operations to strengthen character strokes
    kernel = np.ones((2,2), np.uint8)
    strengthened = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)

    # Thinning to reduce thick strokes
    thinned = cv2.ximgproc.thinning(strengthened)

    # Local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(thinned)

    return enhanced

def repair_after_line_removal(image):
    # Identify potential break points in characters
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(image, kernel, iterations=1)
    potential_breaks = cv2.subtract(dilated, image)

    # Use connected component analysis to find small gaps
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(potential_breaks, connectivity=8)

    # Fill in small gaps
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < 20:  # Adjust threshold as needed
            image[labels == i] = 255

    return image

def detect_content_area(image):
    # Compute vertical and horizontal projection profiles
    vertical_profile = np.sum(image, axis=1)
    horizontal_profile = np.sum(image, axis=0)

    # Smooth the profiles
    smoothed_vertical = np.convolve(vertical_profile, np.ones(50)/50, mode='same')
    smoothed_horizontal = np.convolve(horizontal_profile, np.ones(50)/50, mode='same')

    # Find regions with high density
    v_threshold = np.mean(smoothed_vertical) * 0.5
    h_threshold = np.mean(smoothed_horizontal) * 0.5
    vertical_content = smoothed_vertical > v_threshold
    horizontal_content = smoothed_horizontal > h_threshold

    # Find contiguous regions
    v_diff = np.diff(vertical_content.astype(int))
    h_diff = np.diff(horizontal_content.astype(int))
    v_starts, v_ends = np.where(v_diff == 1)[0] + 1, np.where(v_diff == -1)[0] + 1
    h_starts, h_ends = np.where(h_diff == 1)[0] + 1, np.where(h_diff == -1)[0] + 1

    if len(v_starts) == 0 or len(v_ends) == 0 or len(h_starts) == 0 or len(h_ends) == 0:
        return image  # Return original if no regions found

    # Select the largest regions
    v_region_sizes = v_ends - v_starts
    h_region_sizes = h_ends - h_starts
    largest_v_region = np.argmax(v_region_sizes)
    largest_h_region = np.argmax(h_region_sizes)

    return image[v_starts[largest_v_region]:v_ends[largest_v_region],
                 h_starts[largest_h_region]:h_ends[largest_h_region]]

def preprocess_ancient_chinese_text(image: np.ndarray, params: Dict[str, any] = None) -> Tuple[np.ndarray, List[Tuple[str, np.ndarray]]]:
    print("Starting preprocessing")
    steps = []

    if params is None:
        params = {}

    # Step 1: Resize image if too large
    print("Step 1: Resizing image")
    max_dimension = 2000  # Adjust as needed
    height, width = image.shape[:2]
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    steps.append(("Step 1: Resized Image", image.copy()))

    # Step 2: Determine correct orientation
    print("Step 2: Determining correct orientation")
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

    print(f"Best orientation: {best_orientation} degrees")
    image = ndimage.rotate(image, best_orientation)
    steps.append(("Step 2: Correctly Oriented Image", image.copy()))

    # Step 3: Color channel preprocessing
    print("Step 3: Removing red channel")
    b, g, _ = cv2.split(image)
    no_red = cv2.merge([b, g, np.zeros_like(b)])
    steps.append(("Step 3: Red Channel Removed", no_red.copy()))

    # Modified Step 4: Enhanced Binarization
    print("Step 4: Enhanced Binarization")
    gray = cv2.cvtColor(no_red, cv2.COLOR_BGR2GRAY)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    equalized = clahe.apply(gray)

    # Use Otsu's thresholding after Gaussian filtering
    blur = cv2.GaussianBlur(equalized, (5,5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    steps.append(("Step 4: Enhanced Binarization", binary.copy()))

    # Step 5: Enhance individual characters
    print("Step 5: Enhancing individual characters")
    enhanced = enhance_characters(binary)
    steps.append(("Step 5: Enhanced Characters", enhanced.copy()))

    # Step 6: Fine-tune skew correction
    print("Step 6: Fine-tuning skew")
    coords = np.column_stack(np.where(enhanced > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = enhanced.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(enhanced, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    steps.append(("Step 6: Fine-tuned Skew", deskewed.copy()))

    # Modified Step 7: Improved line removal with repair
    print("Step 7: Improved line removal with repair")

    # Detect and remove long lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

    horizontal_lines = cv2.morphologyEx(deskewed, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    vertical_lines = cv2.morphologyEx(deskewed, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    lines = cv2.add(horizontal_lines, vertical_lines)
    no_lines = cv2.subtract(deskewed, lines)

    # Repair after line removal
    repaired = repair_after_line_removal(no_lines)
    steps.append(("Step 7: Improved line removal with repair", repaired.copy()))

    # Step 8: Detect content area
    print("Step 8: Detecting content area")
    content_area = detect_content_area(repaired)
    steps.append(("Step 8: Content Area Detected", content_area.copy()))

    # Step 9: Remove isolated noise
    print("Step 9: Removing isolated noise")
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(content_area, cv2.MORPH_OPEN, kernel, iterations=2)
    steps.append(("Step 9: Isolated Noise Removed", cleaned.copy()))

    print("Preprocessing complete")
    return cleaned, steps

def segment_characters(image: np.ndarray, params: Dict[str, int] = None, preview: bool = False) -> List[List[Tuple[int, int, int, int]]]:
    print("Starting character segmentation")

    def project_vertically(img: np.ndarray) -> np.ndarray:
        return np.sum(img == 0, axis=0)

    def project_horizontally(img: np.ndarray) -> np.ndarray:
        return np.sum(img == 0, axis=1)

    def find_peaks(projection: np.ndarray, min_distance: int) -> List[int]:
        peaks = []
        for i in range(1, len(projection) - 1):
            if projection[i] > projection[i-1] and projection[i] > projection[i+1] and projection[i] > 0:
                if not peaks or i - peaks[-1] >= min_distance:
                    peaks.append(i)
        return peaks

    def estimate_params(img: np.ndarray) -> Dict[str, int]:
        print("Estimating segmentation parameters...")
        vertical_proj = project_vertically(img)
        horizontal_proj = project_horizontally(img)

        # Estimate column width
        column_widths = np.diff(find_peaks(vertical_proj, img.shape[1] // 10))
        est_column_width = np.median(column_widths) if len(column_widths) > 0 else img.shape[1] // 5

        # Estimate character dimensions
        char_heights = np.diff(find_peaks(horizontal_proj, img.shape[0] // 20))
        est_char_height = np.median(char_heights) if len(char_heights) > 0 else img.shape[0] // 20
        est_char_width = est_char_height  # Assuming square-ish characters

        estimated_params = {
            'min_column_width': max(int(est_column_width * 0.5), 20),
            'min_char_width': max(int(est_char_width * 0.5), 10),
            'min_char_height': max(int(est_char_height * 0.5), 10)
        }
        print(f"Estimated parameters: {estimated_params}")
        return estimated_params

    def segment_columns(img: np.ndarray, min_column_width: int) -> List[np.ndarray]:
        vertical_projection = project_vertically(img)
        column_separators = find_peaks(vertical_projection, min_column_width)
        columns = []
        start = 0
        for end in column_separators + [img.shape[1]]:
            if end - start >= min_column_width:
                columns.append(img[:, start:end])
            start = end
        return columns

    def segment_characters_in_column(column: np.ndarray, min_char_height: int, min_char_width: int) -> List[Tuple[int, int, int, int]]:
        horizontal_projection = project_horizontally(column)
        char_separators = find_peaks(horizontal_projection, min_char_height)
        characters = []
        start_y = 0
        for end_y in char_separators + [column.shape[0]]:
            if end_y - start_y >= min_char_height:
                char_img = column[start_y:end_y, :]
                vertical_projection = project_vertically(char_img)
                char_left = next((i for i, v in enumerate(vertical_projection) if v > 0), 0)
                char_right = next((i for i in range(len(vertical_projection)-1, -1, -1) if vertical_projection[i] > 0), char_img.shape[1])
                if char_right - char_left >= min_char_width:
                    characters.append((char_left, start_y, char_right, end_y))
            start_y = end_y
        return characters

    # Estimate parameters if not provided
    if params is None:
        params = estimate_params(image)
    else:
        print("Using provided parameters:", params)

    # Segment columns
    columns = segment_columns(image, params['min_column_width'])
    print(f"Identified {len(columns)} columns")

    if preview:
        column_preview = image.copy()
        start_x = 0
        for col in columns:
            end_x = start_x + col.shape[1]
            cv2.rectangle(column_preview, (start_x, 0), (end_x, image.shape[0]), (0, 255, 0), 2)
            start_x = end_x
        cv2.imshow("Column Segmentation", column_preview)
        cv2.waitKey(0)

    # Segment characters in each column
    all_characters = []
    start_x = 0
    for i, column in enumerate(columns):
        characters = segment_characters_in_column(column, params['min_char_height'], params['min_char_width'])
        print(f"Identified {len(characters)} characters in column {i+1}")
        all_characters.append([(x + start_x, y, w + start_x, h) for x, y, w, h in characters])
        start_x += column.shape[1]

    if preview:
        char_preview = image.copy()
        for column_chars in all_characters:
            for (x1, y1, x2, y2) in column_chars:
                cv2.rectangle(char_preview, (x1, y1), (x2, y2), (0, 0, 255), 1)
        cv2.imshow("Character Segmentation", char_preview)
        cv2.waitKey(0)

    return all_characters

def process_image(image_path: str, preview: bool = False, manual_params: bool = False) -> List[List[Tuple[int, int, int, int]]]:
    # Load the image
    image = cv2.imread(image_path)  # Convert image_path to string explicitly
    if image is None:
        raise ValueError(f"Unable to read image at {image_path}")

    # Preprocess the image
    preprocessed = preprocess_ancient_chinese_text(image, preview=preview)

    # Get segmentation parameters
    params = None
    if manual_params:
        params = {
            'min_column_width': int(input("Enter minimum column width: ")),
            'min_char_width': int(input("Enter minimum character width: ")),
            'min_char_height': int(input("Enter minimum character height: "))
        }

    # Perform character segmentation
    character_boxes = segment_characters(preprocessed, params, preview)

    return character_boxes
