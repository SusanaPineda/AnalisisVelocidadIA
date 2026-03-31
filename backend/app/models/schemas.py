"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple
from datetime import datetime

class VideoUploadResponse(BaseModel):
    """Response after video upload"""
    video_id: str
    filename: str
    message: str
    uploaded_at: datetime

class AnalysisRequest(BaseModel):
    """Request for video analysis"""
    video_id: str
    climber_weight: float = Field(default=70.0, ge=30.0, le=150.0, description="Climber weight in kg")

class Point2D(BaseModel):
    """2D point coordinates"""
    x: float
    y: float

class Point3D(BaseModel):
    """3D point coordinates"""
    x: float
    y: float
    z: float

class Landmark(BaseModel):
    """Body landmark from MediaPipe"""
    x: float
    y: float
    z: float
    visibility: float

class FrameData(BaseModel):
    """Data for a single frame"""
    frame_number: int
    timestamp: float
    center_of_mass: Point3D
    landmarks: Dict[str, Landmark]
    acceleration: Point3D
    velocity: Point3D

class StepData(BaseModel):
    """Data for a climbing step"""
    step_number: int
    start_time: float
    end_time: float
    duration: float
    start_hold: Point2D
    end_hold: Point2D

class LimbForce(BaseModel):
    """Force estimation for a limb"""
    limb: str  # "left_hand", "right_hand", "left_foot", "right_foot"
    force: float  # Newtons
    position: Point3D

class AnalysisResult(BaseModel):
    """Complete analysis results"""
    video_id: str
    total_duration: float
    reaction_time: float
    total_time: float
    frame_count: int
    fps: float
    frames: List[FrameData]
    steps: List[StepData]
    forces: List[Dict[str, LimbForce]]  # Forces per frame
    power_curve: List[Dict[str, float]]  # Step vs Power (changed from Time vs Power)
    climber_weight: float
    analyzed_at: datetime
    holds: Optional[List[Tuple[int, int]]] = []  # Detected hold positions (x, y) in pixels
    finish_hold_index: Optional[int] = None  # Index of the hold that marks the finish (None if not set)
    last_hold_reached: Optional[int] = None  # Index of the last hold the climber reached (None if no holds reached)
    roi: Optional[Tuple[int, int, int, int]] = None  # ROI used for pose detection (x, y, width, height) in original frame coordinates
    climber_radius: Optional[float] = None  # Radius (pixels) used for climber zone filtering

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
