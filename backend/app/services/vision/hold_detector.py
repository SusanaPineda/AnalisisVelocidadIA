"""
Module for detecting red holds in the climbing wall using HSV thresholding
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from app.core.config import settings

class HoldDetector:
    """Detects red holds in the first frame of a video"""
    
    def __init__(self):
        self.lower_red1 = np.array(settings.RED_HOLD_LOWER_HSV)
        self.upper_red1 = np.array(settings.RED_HOLD_UPPER_HSV)
        self.lower_red2 = np.array(settings.RED_HOLD_LOWER_HSV2)
        self.upper_red2 = np.array(settings.RED_HOLD_UPPER_HSV2)
    
    def detect_holds(self, video_path: str, 
                     lower_hsv1: tuple = None, upper_hsv1: tuple = None,
                     lower_hsv2: tuple = None, upper_hsv2: tuple = None,
                     min_area: int = 100,
                     roi: Optional[Tuple[int, int, int, int]] = None) -> List[Tuple[int, int]]:
        """
        Detect red holds in the first frame of the video
        
        Args:
            video_path: Path to video file
            lower_hsv1: Lower HSV threshold for red (first range)
            upper_hsv1: Upper HSV threshold for red (first range)
            lower_hsv2: Lower HSV threshold for red (second range, wraps around)
            upper_hsv2: Upper HSV threshold for red (second range)
            min_area: Minimum area for a hold in pixels
        
        Returns:
            List of (x, y) coordinates representing hold centers
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError("Could not read first frame")
        
        roi_x_offset = 0
        roi_y_offset = 0
        if roi:
            roi_x, roi_y, roi_w, roi_h = roi
            frame_h, frame_w = frame.shape[:2]

            # Clamp ROI to frame bounds
            roi_x = max(0, min(int(roi_x), frame_w - 1))
            roi_y = max(0, min(int(roi_y), frame_h - 1))
            roi_w = min(int(roi_w), frame_w - roi_x)
            roi_h = min(int(roi_h), frame_h - roi_y)

            roi_x_offset = roi_x
            roi_y_offset = roi_y

            frame = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]

        # Use custom thresholds if provided, otherwise use defaults
        lower1 = np.array(lower_hsv1) if lower_hsv1 else self.lower_red1
        upper1 = np.array(upper_hsv1) if upper_hsv1 else self.upper_red1
        lower2 = np.array(lower_hsv2) if lower_hsv2 else self.lower_red2
        upper2 = np.array(upper_hsv2) if upper_hsv2 else self.upper_red2
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for red color (handles red wrapping around in HSV)
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area and get centroids
        holds = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # Convert back to original-frame coordinates (centroids computed on cropped frame)
                    holds.append((cx + roi_x_offset, cy + roi_y_offset))
        
        # Sort holds by y-coordinate (top to bottom)
        holds.sort(key=lambda h: h[1])
        
        return holds
    
    def get_first_frame(self, video_path: str):
        """
        Get the first frame of the video as a numpy array
        
        Returns:
            First frame as BGR numpy array
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError("Could not read first frame")
        
        return frame