import cv2
import pytesseract
import numpy as np
import pyautogui

from pytesseract import Output

# Custom packages
from screenread import GameWindowHandler
from config import tesseract_location

# Set the OCR executable location
pytesseract.pytesseract.tesseract_cmd = tesseract_location

class OCRProcessor:
    """Processes OCR on specified ROIs within the captured game window."""

    def __init__(self, handler, scale_factor=2):
        """Initializes the OCR processor with a game window handler and scale factor.

        Args:
            handler (GameWindowHandler): The handler for capturing the game window.
            scale_factor (int, optional): The factor to upscale the image for better OCR accuracy. Defaults to 2.
        """
        self.handler = handler
        self.scale_factor = scale_factor

    def find_in_ocr(self, data, text, upscale=True, roi=None):
        """Finds the specified text in the OCR data and returns its center coordinates.

        Args:
            data (dict): The OCR data containing detected text and its coordinates.
            text (str): The text to search for.
            upscale (bool, optional): Whether to use the upscale factor. Defaults to True.
            roi (tuple, optional): The region of interest to adjust the coordinates. Defaults to None.

        Returns:
            tuple: The center coordinates (center_x, center_y) if found, otherwise None.
        """
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            if data['text'][i].strip() == text:
                scale = self.scale_factor if upscale else 1
                left = data['left'][i] // scale
                top = data['top'][i] // scale
                width = data['width'][i] // scale
                height = data['height'][i] // scale

                if roi:
                    roi_left, roi_top, _, _ = roi
                    left += roi_left
                    top += roi_top

                center_x = left + width // 2
                center_y = top + height // 2

                return center_x, center_y

        return None

    def perform_ocr_for_text(self, invert=True, upscale=True, roi=None):
        """Performs OCR on the captured game window or specified ROI.

        Args:
            invert (bool, optional): Whether to invert the image for better OCR accuracy. Defaults to True.
            upscale (bool, optional): Whether to upscale the image for better OCR accuracy. Defaults to True.
            roi (tuple, optional): The region of interest as (x_start, y_start, x_end, y_end). Defaults to None.

        Returns:
            tuple: The OCR data and the coordinates of the ROI in the original image.
        """
        image = self.handler.capture_window()
        original_h, original_w = image.shape[:2]

        if roi:
            x_start, y_start, x_end, y_end = self.obtain_roi(roi, original_h, original_w)
            image = image[round(y_start):round(y_end), round(x_start):round(x_end)]

        if upscale:
            image = cv2.resize(image, None, fx=self.scale_factor, fy=self.scale_factor, interpolation=cv2.INTER_CUBIC)

        processed_image = self.preprocess_image_for_ocr(image, invert)

        if roi:
            roi_left, roi_top, _, _ = self.obtain_roi(roi, original_h, original_w)
            return processed_image, (roi_left, roi_top, x_end, y_end)
        else:
            return processed_image, (0, 0, original_w, original_h)

    def preprocess_image_for_ocr(self, image, invert=True):
        """Preprocesses the image for OCR by sharpening and converting to grayscale.

        Args:
            image (np.ndarray): The image to preprocess.
            invert (bool, optional): Whether to invert the image for better OCR accuracy. Defaults to True.

        Returns:
            dict: The OCR data containing detected text and its coordinates.
        """
        sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(image, -1, sharpen_kernel)

        gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
        if invert: 
            _, binary_image = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            inverted = cv2.bitwise_not(binary_image)
            return pytesseract.image_to_data(inverted, lang='eng', config='--oem 1', output_type=Output.DICT)
        else:
            return pytesseract.image_to_data(sharpened, lang='eng', config='--oem 1', output_type=Output.DICT)

    def obtain_roi(self, roi, h, w):
        """Obtains the ROI coordinates in the image based on the given ROI format.

        Args:
            roi (tuple): The region of interest as (x_start, y_start, x_end, y_end) or a predefined format.
            h (int): The height of the image.
            w (int): The width of the image.

        Returns:
            tuple: The coordinates (x_start, y_start, x_end, y_end) of the ROI.
        """
        if isinstance(roi[0], float) and isinstance(roi[1], float) and isinstance(roi[2], float) and isinstance(roi[3], float):
            x_start = round(w * roi[0])
            y_start = round(h * roi[1])
            x_end = round(w * roi[2])
            y_end = round(h * roi[3])
        elif roi[0] == 'Top':
            x_start, y_start, x_end, y_end = 0, 0, w, round(h * roi[1])
        elif roi[0] == 'Bottom':
            x_start, y_start, x_end, y_end = 0, h - round(h * roi[1]), w, h
        elif roi[0] == 'Left':
            x_start, y_start, x_end, y_end = 0, 0, round(w * roi[1]), h
        elif roi[0] == 'Right':
            x_start, y_start, x_end, y_end = w - round(w * roi[1]), 0, w, h
        elif isinstance(roi[0], int):
            x_start, y_start, x_end, y_end = roi
        else:
            raise ValueError("Invalid ROI format")

        return x_start, y_start, x_end, y_end
    
    def player_ping_ocr(self):
        """Processes the player's ping OCR by capturing and sharpening the game window image.

        Returns:
            np.ndarray: The processed image ready for OCR.
        """
        image = self.handler.capture_window()
        image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(image, -1, sharpen_kernel)

        gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
        _, binary_image = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        inverted = cv2.bitwise_not(binary_image)

        return inverted
    
    def perform_ocr_for_state_engine_text(self, image, roi=None):
        """Performs OCR on a specific region of interest (ROI) within the image.

        Args:
            image (np.ndarray): The captured game window image.
            roi (tuple, optional): The region of interest as (x_start, y_start, x_end, y_end). Defaults to None.

        Returns:
            dict: The OCR data containing detected text and its coordinates.
        """
        h, w = image.shape[:2]
        if roi:
            x_start, y_start, x_end, y_end = int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h)
            image = image[y_start:y_end, x_start:x_end]

        if self.scale_factor > 1:
            image = cv2.resize(image, None, fx=self.scale_factor, fy=self.scale_factor, interpolation=cv2.INTER_CUBIC)

        return self.preprocess_image_for_ocr(image, invert=True)

    def find_text_in_rois(self, image, states_info):
        """Finds specified texts within given ROIs in the captured image.

        Args:
            image (np.ndarray): The captured game window image.
            states_info (dict): A dictionary mapping state names to their info (ROI and text).

        Returns:
            str: The name of the detected state or None if no match is found.
        """
        for state_name, info in states_info.items():
            roi = info['roi']
            text_to_find = info['text']
            ocr_data = self.perform_ocr_for_state_engine_text(image, roi)
            for text in ocr_data['text']:
                if text_to_find in text.strip():
                    return state_name
        return None
    
    def find_and_click(self, search_text, roi):
        """Finds the specified text within the ROI and calculates its center in the original image.

        Args:
            search_text (str): The text to search for.
            roi (tuple): The region of interest as (x_start, y_start, x_end, y_end) in percentages.

        Returns:
            tuple: The center coordinates (center_x, center_y) in the original image if found, otherwise None.
        """
        handler = GameWindowHandler()
        image = handler.capture_window()
        ocr_data = self.perform_ocr_for_state_engine_text(image, roi)
        n_boxes = len(ocr_data['level'])

        h, w = image.shape[:2] # type: ignore
        x_start, y_start, x_end, y_end = int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h)

        handler.pull_foreground()
        
        for i in range(n_boxes):
            if search_text in ocr_data['text'][i].strip():
                left = ocr_data['left'][i] // self.scale_factor
                top = ocr_data['top'][i] // self.scale_factor
                width = ocr_data['width'][i] // self.scale_factor
                height = ocr_data['height'][i] // self.scale_factor
                center_x = left + width // 2
                center_y = top + height // 2
                # Adjust coordinates to original image
                center_x += x_start
                center_y += y_start
                pyautogui.moveTo(center_x, center_y, 0.3)
                pyautogui.leftClick()

    def find_players_to_kick(self, max_latency=130) -> list:
        """Finds players to kick based on their latency.

        Args:
            max_latency (int, optional): The maximum allowed latency. Defaults to 130.

        Returns:
            list: A list of dictionaries containing player names, latencies, and team names.
        """
        inverted = self.player_ping_ocr()

        h, w = inverted.shape[:2]

        text_locations = [
            (round(w * 0.17), round(h * 0.197), round(w * 0.32), round(h * 0.876)),  # Team 1 names
            (round(w * 0.63), round(h * 0.197), round(w * 0.79), round(h * 0.876)),  # Team 2 names
            (round(w * 0.466), round(h * 0.197), round(w * 0.494), round(h * 0.876)), # Team 1 ping
            (round(w * 0.928), round(h * 0.197), round(w * 0.953), round(h * 0.876)), # Team 2 ping
        ]

        mask = np.zeros_like(inverted)
        for (x1, y1, x2, y2) in text_locations:
            mask[y1:y2, x1:x2] = 255

        processed_image = cv2.bitwise_and(inverted, mask)
        mask_inv = cv2.bitwise_not(mask)
        processed_image += mask_inv

        team_one_region = (round(w * 0.17), round(h * 0.197), round(w * 0.494), round(h * 0.876))
        team_two_region = (round(w * 0.63), round(h * 0.197), round(w * 0.953), round(h * 0.876))

        def extract_text_from_region(image, region):
            x1, y1, x2, y2 = region
            cropped_image = image[y1:y2, x1:x2]
            data = pytesseract.image_to_data(cropped_image, config=r'--oem 3 --psm 6', output_type=Output.DICT)
            return data
        
        team_one_data = extract_text_from_region(processed_image, team_one_region)
        team_two_data = extract_text_from_region(processed_image, team_two_region)

        threshold_top = 5
        threshold_left = 500

        paired_players = []
        for team, team_name in zip([team_one_data, team_two_data], ['teamOne', 'teamTwo']):
            valid_players = [(team['text'][i].strip(), team['top'][i], team['left'][i]) for i in range(len(team['level'])) if len(team['text'][i].strip()) > 1]
            for i, (text1, top1, left1) in enumerate(valid_players):
                for j, (text2, top2, left2) in enumerate(valid_players):
                    try:
                        if i != j and abs(top1 - top2) <= threshold_top and abs(left1 - left2) >= threshold_left and left2 > left1 and int(text2) >= max_latency:
                            paired_players.append({'name': text1, 'latency': text2, 'team': team_name})
                    except Exception as e:
                        print(e)

        return paired_players

    def find_player_coords(self, player_name, player_team):
        """Finds the coordinates of a player based on their name and team.

        Args:
            player_name (str): The name of the player.
            player_team (str): The team of the player ('teamOne' or 'teamTwo').

        Returns:
            tuple: The coordinates (center_x, center_y) of the player if found, otherwise None.
        """
        rois = {
            'teamOne': (0.17, 0.197, 0.32, 0.876),
            'teamTwo': (0.628, 0.197, 0.787, 0.876)
        }

        roi = rois.get(player_team)
        
        if roi is None:
            return None

        data, roi_coords = self.perform_ocr_for_text(invert=True, roi=roi)
        coords = self.find_in_ocr(data, player_name, roi=roi_coords)

        return coords if coords else None