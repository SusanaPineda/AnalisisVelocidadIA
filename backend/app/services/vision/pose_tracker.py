"""
Module for tracking human pose using MediaPipe Pose
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple, Optional
from app.core.config import settings

class PoseTracker:
    """Tracks 33 body landmarks using MediaPipe Pose"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.MIN_TRACKING_CONFIDENCE,
            model_complexity=2  # Full 33-point model
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def process_video(
        self,
        video_path: str,
        roi: Optional[Tuple[int, int, int, int]] = None,
        climber_point: Optional[Tuple[int, int]] = None,
        climber_radius: float = 80.0
    ) -> Tuple[List[Dict], float]:
        """
        Process video and extract pose landmarks for each frame
        
        Args:
            video_path: Path to video file
            roi: Optional region of interest (x, y, width, height) to focus detection
        
        Returns:
            Tuple of (frames_data, fps)
            frames_data: List of dicts with frame data
        """
        import logging
        logger = logging.getLogger(__name__)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames_data = []
        frame_number = 0
        pose_detected_count = 0
        
        # Get video dimensions
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        climber_point_norm = None
        climber_radius_norm = None
        if climber_point:
            # Compare in normalized coordinates (0-1) to be robust across resizes/crops.
            cx, cy = climber_point
            cx = max(0, min(int(cx), width - 1))
            cy = max(0, min(int(cy), height - 1))
            climber_point_norm = (cx / width, cy / height)
            climber_radius_norm = float(climber_radius) / max(width, height)
        
        logger.info(f"Processing video: {width}x{height} @ {fps} fps")
        if roi:
            logger.info(f"Using ROI: {roi}")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Store original frame dimensions for coordinate transformation
            original_width = width
            original_height = height
            
            # Apply ROI if specified
            roi_x_offset = 0
            roi_y_offset = 0
            roi_width = width
            roi_height = height
            if roi:
                roi_x, roi_y, roi_w, roi_h = roi
                # Ensure ROI is within frame bounds
                roi_x = max(0, min(roi_x, width - 1))
                roi_y = max(0, min(roi_y, height - 1))
                roi_w = min(roi_w, width - roi_x)
                roi_h = min(roi_h, height - roi_y)
                frame = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
                roi_x_offset = roi_x
                roi_y_offset = roi_y
                roi_width = roi_w
                roi_height = roi_h
            
            # Resize frame if too large (MediaPipe works better with smaller frames)
            # But keep aspect ratio. Use smaller max dimension for better performance
            resize_scale = 1.0
            max_dimension = 960  # Reduced from 1280 for better performance
            if frame.shape[1] > max_dimension or frame.shape[0] > max_dimension:
                resize_scale = max_dimension / max(frame.shape[1], frame.shape[0])
                new_width = int(frame.shape[1] * resize_scale)
                new_height = int(frame.shape[0] * resize_scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.debug(f"Resized frame from {frame.shape[1]}x{frame.shape[0]} to {new_width}x{new_height}")
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            
            # Process frame
            results = self.pose.process(rgb_frame)
            
            # Extract landmarks and transform coordinates back to original frame
            # MediaPipe returns normalized coordinates (0-1) relative to the processed frame
            processed_width = rgb_frame.shape[1]
            processed_height = rgb_frame.shape[0]
            
            landmarks_dict = {}
            has_pose = False
            
            if results.pose_landmarks:
                # Check if we have enough visible landmarks (at least 8, lowered from 10)
                # Use lower visibility threshold (0.3 instead of 0.5) for better detection
                visible_landmarks = sum(1 for lm in results.pose_landmarks.landmark if lm.visibility > 0.3)
                
                if visible_landmarks >= 8:  # Minimum landmarks to consider valid (lowered from 10)
                    has_pose = True
                    
                    for idx, landmark in enumerate(results.pose_landmarks.landmark):
                        # Transform coordinates from processed frame back to original frame
                        # Step 1: MediaPipe gives normalized coordinates (0-1) relative to processed frame
                        # Convert to pixel coordinates in processed frame
                        processed_x = landmark.x * processed_width
                        processed_y = landmark.y * processed_height
                        
                        # Step 2: Apply inverse resize transformation (if frame was resized)
                        if resize_scale < 1.0:
                            roi_frame_x = processed_x / resize_scale
                            roi_frame_y = processed_y / resize_scale
                        else:
                            roi_frame_x = processed_x
                            roi_frame_y = processed_y
                        
                        # Step 3: Apply inverse ROI transformation (add ROI offset to get original frame coordinates)
                        original_x = roi_frame_x + roi_x_offset
                        original_y = roi_frame_y + roi_y_offset
                        
                        # Step 4: Normalize back to 0-1 range for original frame
                        normalized_x = original_x / original_width
                        normalized_y = original_y / original_height
                        
                        landmarks_dict[f"landmark_{idx}"] = {
                            "x": normalized_x,
                            "y": normalized_y,
                            "z": landmark.z,
                            "visibility": landmark.visibility
                        }

                    # Optional filter: keep only poses close to the selected climber point.
                    # This helps when MediaPipe jumps to another person in the frame.
                    if climber_point_norm and climber_radius_norm is not None:
                        # Use shoulder+hip center as a coarse pose center
                        center_indices = [11, 12, 23, 24]  # shoulders and hips
                        cx_vals = []
                        cy_vals = []
                        for cidx in center_indices:
                            key = f"landmark_{cidx}"
                            if key in landmarks_dict:
                                cx_vals.append(landmarks_dict[key]["x"])
                                cy_vals.append(landmarks_dict[key]["y"])

                        if len(cx_vals) == 4:
                            pose_cx = float(np.mean(cx_vals))
                            pose_cy = float(np.mean(cy_vals))
                            dist = float(np.sqrt((pose_cx - climber_point_norm[0]) ** 2 + (pose_cy - climber_point_norm[1]) ** 2))
                            if dist > climber_radius_norm:
                                has_pose = False
                                landmarks_dict = {}
                        else:
                            # If we can't compute the center reliably, be conservative.
                            has_pose = False
                            landmarks_dict = {}

                    if has_pose:
                        pose_detected_count += 1
                else:
                    if frame_number < 5 or frame_number % 50 == 0:  # Log first few and every 50th
                        logger.debug(f"Frame {frame_number}: Only {visible_landmarks} visible landmarks (need 8+)")
            
            frames_data.append({
                "frame_number": frame_number,
                "timestamp": frame_number / fps if fps > 0 else 0,
                "landmarks": landmarks_dict,
                "has_pose": has_pose
            })
            
            frame_number += 1
            
            # Log progress every 50 frames
            if frame_number % 50 == 0:
                logger.info(f"Processed {frame_number} frames, pose detected in {pose_detected_count} frames")
        
        cap.release()
        logger.info(f"Video processing complete: {pose_detected_count}/{frame_number} frames with pose detected")
        
        return frames_data, fps
    
    def get_landmark_coords(self, landmarks_dict: Dict, landmark_idx: int) -> Tuple[float, float, float]:
        """Extract coordinates for a specific landmark"""
        key = f"landmark_{landmark_idx}"
        if key in landmarks_dict:
            lm = landmarks_dict[key]
            return lm["x"], lm["y"], lm["z"]
        return None, None, None
