"""
Module for creating video overlay with skeleton and metrics
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import Dict
from app.models.schemas import AnalysisResult, Landmark

class VideoOverlay:
    """Creates video overlay with pose skeleton and biomechanical metrics"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.3,  # Lowered for better detection
            min_tracking_confidence=0.3,  # Lowered to maintain tracking
            model_complexity=2
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
    
    def create_overlay(self, input_path: str, output_path: str, analysis_result: AnalysisResult):
        """
        Create overlay video with skeleton and metrics
        """
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")
        
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Creating overlay video: {width}x{height} @ {fps} fps")

        # If ROI is provided, we crop the output video to that region.
        roi_crop = None
        if analysis_result.roi:
            roi_x, roi_y, roi_w, roi_h = analysis_result.roi
            # Clamp ROI to original frame bounds
            roi_x = max(0, min(int(roi_x), width - 1))
            roi_y = max(0, min(int(roi_y), height - 1))
            roi_w = min(int(roi_w), width - roi_x)
            roi_h = min(int(roi_h), height - roi_y)
            if roi_w > 0 and roi_h > 0:
                roi_crop = (roi_x, roi_y, roi_w, roi_h)
                logger.info(f"Cropping overlay output to ROI: {roi_crop}")
        
        # Try codecs that work without H.264 encoder
        # Strategy: Try MP4 with mp4v first (some browsers support it), then fallback to AVI
        original_output_path = str(output_path)
        output_path_str = original_output_path
        
        # Try MP4 with mp4v codec first (works in some browsers)
        fourcc_codecs_mp4 = [
            ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),  # MPEG-4 Part 2 in MP4
        ]
        
        # Fallback to AVI with other codecs
        temp_avi_path = output_path_str.replace('.mp4', '.avi')
        fourcc_codecs_avi = [
            ('XVID', cv2.VideoWriter_fourcc(*'XVID')),  # Xvid MPEG-4
            ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),  # Motion JPEG
        ]
        
        out = None
        used_codec = None
        final_output_path = None
        
        # First try MP4 with mp4v
        out_width, out_height = (roi_crop[2], roi_crop[3]) if roi_crop else (width, height)

        if output_path_str.endswith('.mp4'):
            for codec_name, fourcc in fourcc_codecs_mp4:
                out = cv2.VideoWriter(output_path_str, fourcc, fps, (out_width, out_height))
                if out.isOpened():
                    used_codec = codec_name
                    final_output_path = output_path_str
                    logger.info(f"Using codec: {codec_name} with MP4 file: {final_output_path}")
                    break
                else:
                    if out:
                        out.release()
                    out = None
        
        # If MP4 failed, try AVI
        if out is None:
            logger.warning("MP4 with mp4v failed, trying AVI format")
            for codec_name, fourcc in fourcc_codecs_avi:
                out = cv2.VideoWriter(temp_avi_path, fourcc, fps, (out_width, out_height))
                if out.isOpened():
                    used_codec = codec_name
                    final_output_path = temp_avi_path
                    logger.info(f"Using codec: {codec_name} with AVI file: {final_output_path}")
                    break
                else:
                    if out:
                        out.release()
                    out = None
        
        if out is None:
            raise ValueError("Could not initialize video writer with any codec. Make sure OpenCV is properly installed with video codec support.")
        
        frame_idx = 0
        frames_dict = {f.frame_number: f for f in analysis_result.frames}
        
        # Track which holds have been touched (persistent across frames)
        holds_touched = set()
        last_hold_reached = None

        # Precompute ordering of holds from bottom (mayor y) to top (menor y)
        holds_with_index = []
        
        # Log holds information
        if analysis_result.holds:
            for idx, (hx, hy) in enumerate(analysis_result.holds):
                holds_with_index.append({"idx": idx, "x": hx, "y": hy})
            # Ordenar de abajo (y más grande) a arriba (y más pequeño)
            holds_with_index.sort(key=lambda h: h["y"], reverse=True)

            logger.info(f"Drawing {len(analysis_result.holds)} holds in video (bottom-to-top numbering)")
            for display_idx, meta in enumerate(holds_with_index):
                logger.info(f"Hold {display_idx+1}: ({meta['x']}, {meta['y']}) [original index {meta['idx']}]")
        else:
            logger.warning("No holds detected in analysis result")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to RGB for MediaPipe drawing
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = True
            
            # Get frame data if available
            frame_data = frames_dict.get(frame_idx)
            
            # Draw pose skeleton if frame data exists and has landmarks
            if frame_data and frame_data.landmarks and len(frame_data.landmarks) > 0:
                landmarks = self._convert_to_mp_landmarks(frame_data.landmarks)
                if landmarks and len(landmarks.landmark) > 0:
                    try:
                        self.mp_drawing.draw_landmarks(
                            rgb_frame,
                            landmarks,
                            self.mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                        )
                    except Exception as e:
                        logger.warning(f"Error drawing landmarks in frame {frame_idx}: {e}")
            
            # Convert back to BGR
            frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            
            # Draw Center of Mass if frame data exists
            if frame_data:
                com = frame_data.center_of_mass
                com_x = int(com.x * width)
                com_y = int(com.y * height)
                # Validate coordinates are within frame
                if 0 <= com_x < width and 0 <= com_y < height:
                    cv2.circle(frame, (com_x, com_y), 10, (0, 255, 0), -1)
                    cv2.putText(frame, "CoM", (com_x + 15, com_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw ROI if it was provided but we didn't crop the output (debug / legacy mode)
            if analysis_result.roi and not roi_crop:
                roi_x, roi_y, roi_w, roi_h = analysis_result.roi
                # Validate ROI coordinates are within frame
                if 0 <= roi_x < width and 0 <= roi_y < height:
                    # Ensure ROI doesn't exceed frame bounds
                    roi_x_end = min(roi_x + roi_w, width)
                    roi_y_end = min(roi_y + roi_h, height)
                    roi_w_actual = roi_x_end - roi_x
                    roi_h_actual = roi_y_end - roi_y
                    
                    # Draw ROI as yellow border only (no fill)
                    cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w_actual, roi_y + roi_h_actual), 
                                (0, 255, 255), 3)  # Yellow border, 3px thick
                    # Draw ROI label
                    cv2.putText(frame, "ROI", (roi_x + 5, roi_y + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                else:
                    logger.warning(f"ROI coordinates ({roi_x}, {roi_y}, {roi_w}, {roi_h}) out of bounds ({width}x{height})")
            
            # Draw holds on every frame (they don't change)
            # Check which holds are being touched in this frame
            touched_holds_this_frame = set()
            if frame_data and frame_data.landmarks and len(frame_data.landmarks) > 0:
                # Get hand and foot positions (landmarks 15, 16, 27, 28)
                limb_landmarks = [15, 16, 27, 28]  # left_wrist, right_wrist, left_ankle, right_ankle
                for limb_idx in limb_landmarks:
                    key = f"landmark_{limb_idx}"
                    if key in frame_data.landmarks:
                        lm = frame_data.landmarks[key]
                        # Convert normalized coordinates to pixel coordinates
                        limb_x = int(lm.x * width)
                        limb_y = int(lm.y * height)
                        
                        # Check if this limb is near any hold
                        if analysis_result.holds:
                            for hold_idx, (hold_x, hold_y) in enumerate(analysis_result.holds):
                                # Calculate distance between limb and hold
                                distance = np.sqrt((limb_x - hold_x)**2 + (limb_y - hold_y)**2)
                                # If within 30 pixels, consider the hold as touched
                                if distance < 30:
                                    touched_holds_this_frame.add(hold_idx)
                                    holds_touched.add(hold_idx)  # Mark as permanently touched
                                    # Update last hold reached (highest index)
                                    if last_hold_reached is None or hold_idx > last_hold_reached:
                                        last_hold_reached = hold_idx
            
            if analysis_result.holds and len(analysis_result.holds) > 0:
                for display_idx, meta in enumerate(holds_with_index):
                    hold_idx = meta["idx"]
                    hold_x = meta["x"]
                    hold_y = meta["y"]
                    # Validate coordinates are within frame
                    if 0 <= hold_x < width and 0 <= hold_y < height:
                        is_finish_hold = analysis_result.finish_hold_index == hold_idx
                        is_touched = hold_idx in holds_touched  # Check if ever touched
                        is_last_reached = last_hold_reached == hold_idx
                        
                        # Change color based on state
                        if is_touched:
                            # Green when touched (stays green once touched)
                            cv2.circle(frame, (hold_x, hold_y), 15, (0, 255, 0), -1)  # Green filled circle
                            cv2.circle(frame, (hold_x, hold_y), 15, (255, 255, 255), 2)  # White border
                            # Highlight last reached hold
                            if is_last_reached:
                                cv2.circle(frame, (hold_x, hold_y), 20, (0, 255, 255), 3)  # Yellow outer ring
                                cv2.putText(frame, "ULTIMA", (hold_x - 20, hold_y - 25), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 2)
                        elif is_finish_hold:
                            # Purple/violet for finish hold when not touched (different from red and green)
                            cv2.circle(frame, (hold_x, hold_y), 15, (226, 43, 138), -1)  # BlueViolet (BGR format)
                            cv2.circle(frame, (hold_x, hold_y), 15, (0, 215, 255), 3)  # Gold border (thicker)
                            # Draw "FIN" label
                            cv2.putText(frame, "FIN", (hold_x - 10, hold_y + 25), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 215, 255), 1)
                        else:
                            # Red when not touched
                            cv2.circle(frame, (hold_x, hold_y), 15, (0, 0, 255), -1)  # Red filled circle
                            cv2.circle(frame, (hold_x, hold_y), 15, (255, 255, 255), 2)  # White border
                        # Draw hold number (bottom-to-top: 1 = más abajo)
                        cv2.putText(frame, str(display_idx + 1), (hold_x - 5, hold_y + 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    else:
                        logger.warning(f"Hold {hold_idx+1} coordinates ({hold_x}, {hold_y}) out of bounds ({width}x{height})")
            
            # Draw metrics text on every frame
            if frame_data:
                metrics_text = [
                    f"Time: {frame_data.timestamp:.2f}s",
                    f"Acceleration: {np.sqrt(frame_data.acceleration.x**2 + frame_data.acceleration.y**2):.2f} m/s²"
                ]
                # Show last hold reached (using display number bottom-to-top)
                if last_hold_reached is not None and holds_with_index:
                    # Map original index to display index
                    meta = next((m for m in holds_with_index if m["idx"] == last_hold_reached), None)
                    if meta is not None:
                        display_num = holds_with_index.index(meta) + 1
                        metrics_text.append(f"Ultima presa: {display_num}")
            else:
                metrics_text = [f"Frame: {frame_idx}"]
            
            y_offset = 30
            for text in metrics_text:
                cv2.putText(frame, text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 25
            
            if roi_crop:
                roi_x, roi_y, roi_w, roi_h = roi_crop
                cropped = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
                out.write(cropped)
            else:
                out.write(frame)
            frame_idx += 1
        
        logger.info(f"Processed {frame_idx} frames")
        
        cap.release()
        out.release()
        
        # Verify file was created
        if os.path.exists(final_output_path):
            file_size = os.path.getsize(final_output_path)
            logger.info(f"Video created successfully: {final_output_path} ({file_size} bytes)")
            if file_size == 0:
                raise ValueError("Video file was created but is empty")
            
            # Always try to convert to MP4 with H.264 using ffmpeg if available
            # This improves browser compatibility significantly
            if original_output_path.endswith('.mp4'):
                try:
                    import subprocess
                    # Check if ffmpeg is available
                    result = subprocess.run(['ffmpeg', '-version'], 
                                          capture_output=True, 
                                          timeout=5)
                    if result.returncode == 0:
                        logger.info(f"Converting {final_output_path} to MP4 with H.264 using ffmpeg...")
                        # Use a temporary file for conversion (ffmpeg cannot edit in-place)
                        temp_output_path = original_output_path.replace('.mp4', '_temp_h264.mp4')
                        # Convert to MP4 with H.264
                        convert_cmd = [
                            'ffmpeg', '-y', '-i', final_output_path,
                            '-c:v', 'libx264', '-preset', 'medium',
                            '-crf', '23', '-pix_fmt', 'yuv420p',  # yuv420p for better compatibility
                            '-movflags', '+faststart',  # Enable fast start for web streaming
                            temp_output_path
                        ]
                        convert_result = subprocess.run(convert_cmd, 
                                                       capture_output=True,
                                                       timeout=300)  # 5 min timeout
                        if convert_result.returncode == 0 and os.path.exists(temp_output_path):
                            logger.info(f"Successfully converted to MP4 with H.264: {temp_output_path}")
                            # Replace original file with converted one
                            if os.path.exists(original_output_path):
                                os.remove(original_output_path)
                            os.rename(temp_output_path, original_output_path)
                            # Remove temporary file if different
                            if final_output_path != original_output_path and os.path.exists(final_output_path):
                                os.remove(final_output_path)
                            final_output_path = original_output_path
                        else:
                            error_msg = convert_result.stderr.decode() if convert_result.stderr else "Unknown error"
                            logger.warning(f"ffmpeg conversion failed: {error_msg}")
                            logger.warning(f"Keeping original file: {final_output_path}")
                            # Clean up temp file if it exists
                            if os.path.exists(temp_output_path):
                                os.remove(temp_output_path)
                    else:
                        logger.warning("ffmpeg not available. To install: sudo apt install ffmpeg")
                        logger.warning(f"Keeping file: {final_output_path}")
                except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                    logger.warning(f"ffmpeg not available: {e}. To install: sudo apt install ffmpeg")
                    logger.warning(f"Keeping file: {final_output_path}")
                except Exception as e:
                    logger.warning(f"Error during conversion: {e}. Keeping file: {final_output_path}")
        else:
            raise ValueError("Video file was not created")
    
    def _convert_to_mp_landmarks(self, landmarks_dict: Dict[str, Landmark]):
        """Convert landmarks dict to MediaPipe landmarks format"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from mediapipe.framework.formats import landmark_pb2
            landmarks = landmark_pb2.NormalizedLandmarkList()
            
            landmarks_added = 0
            for i in range(33):  # MediaPipe Pose has 33 landmarks
                key = f"landmark_{i}"
                if key in landmarks_dict:
                    lm = landmarks_dict[key]
                    landmark = landmarks.landmark.add()
                    landmark.x = lm.x
                    landmark.y = lm.y
                    landmark.z = lm.z
                    landmark.visibility = lm.visibility
                    landmarks_added += 1
            
            if landmarks_added == 0:
                logger.warning("No landmarks found in landmarks_dict")
                return None
            
            logger.debug(f"Converted {landmarks_added} landmarks to MediaPipe format")
            return landmarks
        except ImportError as e:
            logger.error(f"Failed to import MediaPipe landmark format: {e}")
            return None
        except Exception as e:
            logger.error(f"Error converting landmarks: {e}")
            return None
