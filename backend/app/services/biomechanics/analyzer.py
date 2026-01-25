"""
Biomechanical analysis module for speed climbing
Calculates Center of Mass, reaction times, step times, and forces
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from app.models.schemas import (
    AnalysisResult, FrameData, StepData, LimbForce, 
    Point3D, Point2D, Landmark
)
from app.core.config import settings

class BiomechanicalAnalyzer:
    """Performs biomechanical analysis on pose tracking data"""
    
    # MediaPipe Pose landmark indices
    # Key points for CoM calculation (approximate body segments)
    LANDMARK_INDICES = {
        "head": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28
    }
    
    # Approximate body segment masses (as percentage of total body mass)
    SEGMENT_MASSES = {
        "head": 0.08,
        "torso": 0.50,
        "upper_arm": 0.03,
        "forearm": 0.02,
        "hand": 0.01,
        "thigh": 0.10,
        "shank": 0.05,
        "foot": 0.01
    }
    
    def __init__(self, climber_weight: float = 70.0):
        self.climber_weight = climber_weight
        self.gravity = settings.GRAVITY
        self.smoothing_window = settings.SMOOTHING_WINDOW
    
    def calculate_center_of_mass(self, landmarks_dict: Dict) -> Point3D:
        """
        Calculate Center of Mass from body landmarks
        Uses simplified model with key body segments
        """
        if not landmarks_dict:
            return Point3D(x=0.5, y=0.5, z=0)
        
        # Get key landmarks
        key_points = {}
        for name, idx in self.LANDMARK_INDICES.items():
            key = f"landmark_{idx}"
            if key in landmarks_dict:
                lm = landmarks_dict[key]
                key_points[name] = (lm["x"], lm["y"], lm["z"])
        
        if not key_points:
            return Point3D(x=0.5, y=0.5, z=0)
        
        # Simplified CoM calculation using weighted average of key points
        # Approximate body segment positions
        com_x, com_y, com_z = 0.0, 0.0, 0.0
        total_weight = 0.0
        
        # Head
        if "head" in key_points:
            weight = self.SEGMENT_MASSES["head"]
            com_x += key_points["head"][0] * weight
            com_y += key_points["head"][1] * weight
            com_z += key_points["head"][2] * weight
            total_weight += weight
        
        # Torso (average of shoulders and hips)
        if all(k in key_points for k in ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]):
            torso_x = (key_points["left_shoulder"][0] + key_points["right_shoulder"][0] + 
                      key_points["left_hip"][0] + key_points["right_hip"][0]) / 4
            torso_y = (key_points["left_shoulder"][1] + key_points["right_shoulder"][1] + 
                      key_points["left_hip"][1] + key_points["right_hip"][1]) / 4
            torso_z = (key_points["left_shoulder"][2] + key_points["right_shoulder"][2] + 
                      key_points["left_hip"][2] + key_points["right_hip"][2]) / 4
            weight = self.SEGMENT_MASSES["torso"]
            com_x += torso_x * weight
            com_y += torso_y * weight
            com_z += torso_z * weight
            total_weight += weight
        
        # Limbs (simplified)
        for limb_type in ["left", "right"]:
            # Upper arm
            if f"{limb_type}_shoulder" in key_points and f"{limb_type}_elbow" in key_points:
                mid_x = (key_points[f"{limb_type}_shoulder"][0] + key_points[f"{limb_type}_elbow"][0]) / 2
                mid_y = (key_points[f"{limb_type}_shoulder"][1] + key_points[f"{limb_type}_elbow"][1]) / 2
                mid_z = (key_points[f"{limb_type}_shoulder"][2] + key_points[f"{limb_type}_elbow"][2]) / 2
                weight = self.SEGMENT_MASSES["upper_arm"]
                com_x += mid_x * weight
                com_y += mid_y * weight
                com_z += mid_z * weight
                total_weight += weight
            
            # Thigh
            if f"{limb_type}_hip" in key_points and f"{limb_type}_knee" in key_points:
                mid_x = (key_points[f"{limb_type}_hip"][0] + key_points[f"{limb_type}_knee"][0]) / 2
                mid_y = (key_points[f"{limb_type}_hip"][1] + key_points[f"{limb_type}_knee"][1]) / 2
                mid_z = (key_points[f"{limb_type}_hip"][2] + key_points[f"{limb_type}_knee"][2]) / 2
                weight = self.SEGMENT_MASSES["thigh"]
                com_x += mid_x * weight
                com_y += mid_y * weight
                com_z += mid_z * weight
                total_weight += weight
        
        if total_weight > 0:
            com_x /= total_weight
            com_y /= total_weight
            com_z /= total_weight
        
        return Point3D(x=com_x, y=com_y, z=com_z)
    
    def smooth_data(self, data: List[float]) -> List[float]:
        """Apply moving average filter to smooth data"""
        if len(data) < self.smoothing_window:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - self.smoothing_window // 2)
            end = min(len(data), i + self.smoothing_window // 2 + 1)
            smoothed.append(np.mean(data[start:end]))
        
        return smoothed
    
    def calculate_velocity_and_acceleration(self, com_positions: List[Point3D], timestamps: List[float], fps: float) -> Tuple[List[Point3D], List[Point3D]]:
        """Calculate velocity and acceleration from CoM positions"""
        velocities = [Point3D(x=0, y=0, z=0)]
        accelerations = [Point3D(x=0, y=0, z=0)]
        
        dt = 1.0 / fps if fps > 0 else 0.033
        
        for i in range(1, len(com_positions)):
            # Velocity
            vx = (com_positions[i].x - com_positions[i-1].x) / dt
            vy = (com_positions[i].y - com_positions[i-1].y) / dt
            vz = (com_positions[i].z - com_positions[i-1].z) / dt
            velocities.append(Point3D(x=vx, y=vy, z=vz))
            
            # Acceleration
            if i > 1:
                ax = (velocities[i].x - velocities[i-1].x) / dt
                ay = (velocities[i].y - velocities[i-1].y) / dt
                az = (velocities[i].z - velocities[i-1].z) / dt
                accelerations.append(Point3D(x=ax, y=ay, z=az))
            else:
                accelerations.append(Point3D(x=0, y=0, z=0))
        
        # Smooth accelerations
        ax_list = [a.x for a in accelerations]
        ay_list = [a.y for a in accelerations]
        az_list = [a.z for a in accelerations]
        
        ax_smooth = self.smooth_data(ax_list)
        ay_smooth = self.smooth_data(ay_list)
        az_smooth = self.smooth_data(az_list)
        
        accelerations_smooth = [
            Point3D(x=ax_smooth[i], y=ay_smooth[i], z=az_smooth[i])
            for i in range(len(accelerations))
        ]
        
        return velocities, accelerations_smooth
    
    def calculate_reaction_time(self, accelerations: List[Point3D], timestamps: List[float], threshold: float = 0.5) -> float:
        """
        Calculate reaction time based on CoM acceleration threshold
        Reaction time is when acceleration exceeds threshold
        """
        for i, acc in enumerate(accelerations):
            acc_magnitude = np.sqrt(acc.x**2 + acc.y**2 + acc.z**2)
            if acc_magnitude > threshold:
                return timestamps[i]
        return 0.0
    
    def detect_steps(self, com_positions: List[Point3D], holds: List[Tuple[int, int]], timestamps: List[float], frame_width: int = 1920, frame_height: int = 1080) -> List[StepData]:
        """
        Detect climbing steps by tracking when CoM crosses hold thresholds
        """
        steps = []
        if not holds:
            return steps
        
        # Convert holds to normalized coordinates (assuming they're in pixel coordinates)
        normalized_holds = [(x / frame_width, y / frame_height) for x, y in holds]
        
        current_step = 0
        step_start_time = timestamps[0] if timestamps else 0
        
        for i, com in enumerate(com_positions):
            # Check if CoM has crossed a hold threshold (vertical position)
            if current_step < len(normalized_holds):
                target_hold_y = normalized_holds[current_step][1]
                
                # If CoM has passed the current hold
                if com.y >= target_hold_y:
                    step_end_time = timestamps[i] if i < len(timestamps) else timestamps[-1]
                    steps.append(StepData(
                        step_number=current_step + 1,
                        start_time=step_start_time,
                        end_time=step_end_time,
                        duration=step_end_time - step_start_time,
                        start_hold=Point2D(x=normalized_holds[current_step][0], y=normalized_holds[current_step][1]) if current_step > 0 else Point2D(x=0, y=0),
                        end_hold=Point2D(x=normalized_holds[current_step][0], y=normalized_holds[current_step][1])
                    ))
                    step_start_time = step_end_time
                    current_step += 1
        
        return steps
    
    def calculate_limb_forces(self, frame_data: Dict, com: Point3D, acceleration: Point3D) -> List[LimbForce]:
        """
        Estimate forces on each limb using F = m * (g + a)
        Force distribution based on proximity to active supports
        """
        forces = []
        landmarks = frame_data.get("landmarks", {})
        
        # Get limb positions
        limb_positions = {}
        for limb_name in ["left_hand", "right_hand", "left_foot", "right_foot"]:
            if limb_name == "left_hand":
                idx = 15
            elif limb_name == "right_hand":
                idx = 16
            elif limb_name == "left_foot":
                idx = 27
            elif limb_name == "right_foot":
                idx = 28
            
            key = f"landmark_{idx}"
            if key in landmarks:
                lm = landmarks[key]
                limb_positions[limb_name] = Point3D(x=lm["x"], y=lm["y"], z=lm["z"])
        
        if not limb_positions:
            return forces
        
        # Calculate total acceleration magnitude
        acc_magnitude = np.sqrt(acceleration.x**2 + acceleration.y**2 + acceleration.z**2)
        total_acc = self.gravity + acc_magnitude
        
        # Distribute force based on distance from CoM (closer = more force)
        total_distance = 0.0
        distances = {}
        
        for limb_name, limb_pos in limb_positions.items():
            dist = np.sqrt(
                (limb_pos.x - com.x)**2 + 
                (limb_pos.y - com.y)**2 + 
                (limb_pos.z - com.z)**2
            )
            distances[limb_name] = dist
            total_distance += dist
        
        # Calculate forces (inverse distance weighting)
        for limb_name, limb_pos in limb_positions.items():
            if total_distance > 0:
                # Weight inversely proportional to distance
                weight_factor = 1.0 / (distances[limb_name] + 0.1)  # Add small value to avoid division by zero
                # Normalize
                total_weight = sum(1.0 / (d + 0.1) for d in distances.values())
                force_fraction = weight_factor / total_weight if total_weight > 0 else 0.25
            else:
                force_fraction = 1.0 / len(limb_positions)
            
            force = self.climber_weight * total_acc * force_fraction
            forces.append(LimbForce(
                limb=limb_name,
                force=force,
                position=limb_pos
            ))
        
        return forces
    
    def analyze(self, frames_data: List[Dict], holds: List[Tuple[int, int]], fps: float, video_id: str, roi: Optional[Tuple[int, int, int, int]] = None, finish_hold_index: Optional[int] = None, video_width: Optional[int] = None, video_height: Optional[int] = None) -> AnalysisResult:
        """
        Perform complete biomechanical analysis
        """
        # Use video dimensions for coordinate conversion (default to common values if not provided)
        if video_width is None:
            video_width = 1920
        if video_height is None:
            video_height = 1080
        
        # Calculate CoM for each frame
        com_positions = []
        timestamps = []
        
        for frame_data in frames_data:
            if frame_data.get("has_pose", False):
                com = self.calculate_center_of_mass(frame_data.get("landmarks", {}))
            else:
                com = Point3D(x=0.5, y=0.5, z=0)
            com_positions.append(com)
            timestamps.append(frame_data.get("timestamp", 0))
        
        # Smooth CoM positions
        com_x_smooth = self.smooth_data([c.x for c in com_positions])
        com_y_smooth = self.smooth_data([c.y for c in com_positions])
        com_z_smooth = self.smooth_data([c.z for c in com_positions])
        com_positions_smooth = [
            Point3D(x=com_x_smooth[i], y=com_y_smooth[i], z=com_z_smooth[i])
            for i in range(len(com_positions))
        ]
        
        # Calculate velocity and acceleration
        velocities, accelerations = self.calculate_velocity_and_acceleration(
            com_positions_smooth, timestamps, fps
        )
        
        # Calculate reaction time
        reaction_time = self.calculate_reaction_time(accelerations, timestamps)
        
        # Detect steps
        steps = self.detect_steps(com_positions_smooth, holds, timestamps)
        
        # Track which holds have been reached
        holds_reached = set()
        last_hold_reached = None
        
        # Build frame data with all metrics
        frames_result = []
        forces_per_frame = []
        
        for i, frame_data in enumerate(frames_data):
            com = com_positions_smooth[i] if i < len(com_positions_smooth) else Point3D(x=0.5, y=0.5, z=0)
            vel = velocities[i] if i < len(velocities) else Point3D(x=0, y=0, z=0)
            acc = accelerations[i] if i < len(accelerations) else Point3D(x=0, y=0, z=0)
            
            # Check if any hold is being touched in this frame
            if frame_data.get("has_pose", False) and holds:
                landmarks = frame_data.get("landmarks", {})
                # Get hand and foot positions (landmarks 15, 16, 27, 28)
                for limb_idx in [15, 16, 27, 28]:
                    key = f"landmark_{limb_idx}"
                    if key in landmarks:
                        lm = landmarks[key]
                        # Use normalized coordinates to check proximity to holds
                        for hold_idx, (hold_x, hold_y) in enumerate(holds):
                            # Convert hold coordinates (pixels) to normalized coordinates
                            hold_x_norm = hold_x / video_width
                            hold_y_norm = hold_y / video_height
                            distance_norm = np.sqrt((lm["x"] - hold_x_norm)**2 + (lm["y"] - hold_y_norm)**2)
                            if distance_norm < 0.02:  # Normalized threshold
                                holds_reached.add(hold_idx)
                                if last_hold_reached is None or hold_idx > last_hold_reached:
                                    last_hold_reached = hold_idx
            
            # Convert landmarks to schema format
            landmarks_schema = {}
            if frame_data.get("has_pose", False):
                for key, value in frame_data.get("landmarks", {}).items():
                    landmarks_schema[key] = Landmark(
                        x=value["x"],
                        y=value["y"],
                        z=value["z"],
                        visibility=value.get("visibility", 1.0)
                    )
            
            frame_result = FrameData(
                frame_number=frame_data.get("frame_number", i),
                timestamp=frame_data.get("timestamp", i / fps if fps > 0 else 0),
                center_of_mass=com,
                landmarks=landmarks_schema,
                acceleration=acc,
                velocity=vel
            )
            frames_result.append(frame_result)
            
            # Calculate forces
            if frame_data.get("has_pose", False):
                forces = self.calculate_limb_forces(frame_data, com, acc)
                forces_per_frame.append({f.limb: f for f in forces})
            else:
                forces_per_frame.append({})
        
        # Calculate power curve per step (not per time)
        power_curve = []
        for step_idx, step in enumerate(steps):
            # Find frames within this step's time range
            step_frames = []
            for i, frame_result in enumerate(frames_result):
                if step.start_time <= frame_result.timestamp <= step.end_time:
                    step_frames.append((i, frame_result))
            
            # Calculate average power for this step
            step_powers = []
            for frame_idx, frame_result in step_frames:
                if frame_idx < len(forces_per_frame) and forces_per_frame[frame_idx]:
                    # Calculate power for this frame
                    total_force = sum(f.force for f in forces_per_frame[frame_idx].values())
                    vel = velocities[frame_idx] if frame_idx < len(velocities) else Point3D(x=0, y=0, z=0)
                    vel_magnitude = np.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                    power = total_force * vel_magnitude
                    step_powers.append(power)
            
            # Average power for the step
            avg_power = np.mean(step_powers) if step_powers else 0.0
            power_curve.append({
                "step": step.step_number,
                "power": avg_power
            })
        
        # Calculate total time based on finish hold if specified
        total_time = timestamps[-1] if timestamps else 0
        if finish_hold_index is not None and finish_hold_index < len(holds):
            finish_hold_x, finish_hold_y = holds[finish_hold_index]
            
            # Find when any limb touches the finish hold
            # Convert finish hold coordinates (pixels) to normalized coordinates
            finish_hold_x_norm = finish_hold_x / video_width
            finish_hold_y_norm = finish_hold_y / video_height
            
            # Calculate threshold: approximately 40 pixels in normalized space
            # This is more lenient to account for detection variations
            threshold_pixels = 40.0
            threshold_norm = threshold_pixels / max(video_width, video_height)
            
            print(f"Looking for finish hold contact: hold {finish_hold_index + 1} at ({finish_hold_x}, {finish_hold_y})")
            print(f"Normalized: ({finish_hold_x_norm:.4f}, {finish_hold_y_norm:.4f}), threshold: {threshold_norm:.4f}")
            
            finish_hold_touched = False
            for i, frame_data in enumerate(frames_data):
                if frame_data.get("has_pose", False):
                    landmarks = frame_data.get("landmarks", {})
                    # Check hand and foot positions (15, 16, 27, 28)
                    for limb_idx in [15, 16, 27, 28]:
                        key = f"landmark_{limb_idx}"
                        if key in landmarks:
                            lm = landmarks[key]
                            # Use normalized coordinates for comparison
                            # Calculate distance in normalized space
                            distance_norm = np.sqrt((lm["x"] - finish_hold_x_norm)**2 + (lm["y"] - finish_hold_y_norm)**2)
                            if distance_norm < threshold_norm:
                                total_time = timestamps[i] if i < len(timestamps) else timestamps[-1]
                                finish_hold_touched = True
                                print(f"Finish hold touched at frame {i}, time {total_time:.3f}s (distance: {distance_norm:.4f})")
                                break
                    if finish_hold_touched:
                        break
            
            if not finish_hold_touched:
                print(f"WARNING: Finish hold was never touched. Using full video duration: {total_time:.3f}s")
        
        # Log last hold reached info
        if last_hold_reached is not None:
            print(f"Last hold reached: {last_hold_reached} (Presa {last_hold_reached + 1})")
        else:
            print("Last hold reached: None (no holds were touched)")
        
        if finish_hold_index is not None:
            print(f"Finish hold index: {finish_hold_index} (Presa {finish_hold_index + 1})")
            if last_hold_reached is not None:
                completed = last_hold_reached >= finish_hold_index
                print(f"Route completed: {completed} (last_hold_reached={last_hold_reached}, finish_hold_index={finish_hold_index})")
        else:
            print("Finish hold index: None (no finish hold defined)")
        
        return AnalysisResult(
            video_id=video_id,
            total_duration=total_time,
            reaction_time=reaction_time,
            total_time=total_time,
            frame_count=len(frames_data),
            fps=fps,
            frames=frames_result,
            steps=steps,
            forces=forces_per_frame,
            power_curve=power_curve,
            climber_weight=self.climber_weight,
            analyzed_at=datetime.now(),
            holds=holds,
            finish_hold_index=finish_hold_index,
            last_hold_reached=last_hold_reached,
            roi=roi
        )
