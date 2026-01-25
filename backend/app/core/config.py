"""
Configuration settings for the application
"""
import os
from pathlib import Path

class Settings:
    """Application settings"""
    
    # Base directories
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    PROCESSED_DIR = BASE_DIR / "processed"
    
    # Video settings
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
    
    # MediaPipe settings
    MIN_DETECTION_CONFIDENCE = 0.3  # Lowered for better detection
    MIN_TRACKING_CONFIDENCE = 0.3  # Lowered to maintain tracking
    
    # Biomechanical analysis settings
    DEFAULT_CLIMBER_WEIGHT = 70.0  # kg
    GRAVITY = 9.81  # m/s²
    SMOOTHING_WINDOW = 5  # frames for moving average
    
    # HSV thresholds for red hold detection
    RED_HOLD_LOWER_HSV = (0, 100, 100)
    RED_HOLD_UPPER_HSV = (10, 255, 255)
    RED_HOLD_LOWER_HSV2 = (170, 100, 100)  # Red wraps around in HSV
    RED_HOLD_UPPER_HSV2 = (180, 255, 255)
    
    def __init__(self):
        # Create directories if they don't exist
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.PROCESSED_DIR.mkdir(exist_ok=True)

settings = Settings()
