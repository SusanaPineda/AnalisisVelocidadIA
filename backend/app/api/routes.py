"""
API routes for video upload and analysis
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse, Response
import uuid
from pathlib import Path
import cv2
import base64
from typing import List, Tuple

from app.models.schemas import (
    VideoUploadResponse, 
    AnalysisResult
)
from app.core.config import settings
from app.services.vision.pose_tracker import PoseTracker
from app.services.vision.hold_detector import HoldDetector
from app.services.biomechanics.analyzer import BiomechanicalAnalyzer
from datetime import datetime

router = APIRouter()

# In-memory storage for analysis results (in production, use a database)
analysis_results = {}
video_metadata = {}

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for analysis
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Generate unique video ID
    video_id = str(uuid.uuid4())
    filename = f"{video_id}{file_ext}"
    filepath = settings.UPLOAD_DIR / filename
    
    # Save uploaded file
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            f.write(content)
        
        # Store metadata
        video_metadata[video_id] = {
            "filename": file.filename,
            "filepath": str(filepath),
            "uploaded_at": datetime.now().isoformat()
        }
        
        return VideoUploadResponse(
            video_id=video_id,
            filename=file.filename,
            message="Video uploaded successfully",
            uploaded_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.get("/analyze/{video_id}", response_model=AnalysisResult)
async def analyze_video_legacy(video_id: str, climber_weight: float = 70.0):
    """
    Analyze a video and return biomechanical data
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already analyzed
    if video_id in analysis_results:
        return analysis_results[video_id]
    
    filepath = Path(video_metadata[video_id]["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        # Initialize components
        hold_detector = HoldDetector()
        pose_tracker = PoseTracker()
        analyzer = BiomechanicalAnalyzer(climber_weight=climber_weight)
        
        # Detect holds in first frame
        holds = hold_detector.detect_holds(str(filepath))
        print(f"Detected {len(holds)} holds: {holds}")
        
        # Process video and track pose
        frames_data, fps = pose_tracker.process_video(str(filepath))
        print(f"Processed {len(frames_data)} frames at {fps} fps")
        
        # Count frames with pose detection
        frames_with_pose = sum(1 for f in frames_data if f.get("has_pose", False))
        print(f"Frames with pose detected: {frames_with_pose}/{len(frames_data)}")
        
        # Perform biomechanical analysis
        result = analyzer.analyze(frames_data, holds, fps, video_id)
        print(f"Analysis complete. Result holds: {len(result.holds) if result.holds else 0}")
        
        # Store result
        analysis_results[video_id] = result
        
        return result
        
    except Exception as e:
        import traceback
        error_detail = f"Error analyzing video: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/overlay/{video_id}")
async def get_overlay_video(video_id: str):
    """
    Get the processed video with skeleton overlay and metrics
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Video not analyzed yet. Call /analyze first")
    
    filepath = Path(video_metadata[video_id]["filepath"])
    output_path_mp4 = settings.PROCESSED_DIR / f"{video_id}_overlay.mp4"
    output_path_avi = settings.PROCESSED_DIR / f"{video_id}_overlay.avi"
    
    # Check which file exists (MP4 or AVI)
    output_path = None
    media_type = None
    filename = None
    
    if output_path_mp4.exists():
        output_path = output_path_mp4
        media_type = "video/mp4"
        filename = f"{video_id}_overlay.mp4"
    elif output_path_avi.exists():
        output_path = output_path_avi
        media_type = "video/x-msvideo"  # AVI MIME type
        filename = f"{video_id}_overlay.avi"
    else:
        # Generate overlay video if it doesn't exist
        try:
            # Generate overlay video (will create MP4 or AVI depending on codec availability)
            from app.services.vision.video_overlay import VideoOverlay
            overlay_generator = VideoOverlay()
            overlay_generator.create_overlay(
                str(filepath),
                str(output_path_mp4),  # Pass desired MP4 path, may create AVI if needed
                analysis_results[video_id]
            )
            
            # Check which file was actually created
            if output_path_mp4.exists():
                output_path = output_path_mp4
                media_type = "video/mp4"
                filename = f"{video_id}_overlay.mp4"
            elif output_path_avi.exists():
                output_path = output_path_avi
                media_type = "video/x-msvideo"
                filename = f"{video_id}_overlay.avi"
            else:
                raise HTTPException(status_code=500, detail="Video file was not created successfully")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating overlay: {str(e)}")
    
    # Return file with proper headers for video streaming
    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        filename=filename,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(output_path.stat().st_size)
        }
    )

@router.get("/pose-stats/{video_id}")
async def get_pose_detection_stats(video_id: str):
    """
    Get pose detection statistics for a video (for debugging)
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    filepath = Path(video_metadata[video_id]["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        # Process a sample of frames to get stats
        pose_tracker = PoseTracker()
        cap = cv2.VideoCapture(str(filepath))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Sample first 10 frames
        sample_frames = []
        cap = cv2.VideoCapture(str(filepath))
        for i in range(min(10, total_frames)):
            ret, frame = cap.read()
            if not ret:
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = pose_tracker.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                visible = sum(1 for lm in results.pose_landmarks.landmark if lm.visibility > 0.3)
                sample_frames.append({
                    "frame": i,
                    "detected": True,
                    "visible_landmarks": visible
                })
            else:
                sample_frames.append({
                    "frame": i,
                    "detected": False,
                    "visible_landmarks": 0
                })
        cap.release()
        
        detected_count = sum(1 for f in sample_frames if f["detected"])
        
        return {
            "video_info": {
                "width": width,
                "height": height,
                "fps": fps,
                "total_frames": total_frames
            },
            "sample_stats": {
                "frames_tested": len(sample_frames),
                "frames_detected": detected_count,
                "detection_rate": detected_count / len(sample_frames) if sample_frames else 0,
                "sample_frames": sample_frames
            },
            "recommendations": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pose stats: {str(e)}")

@router.get("/first-frame/{video_id}")
async def get_first_frame(video_id: str):
    """
    Get the first frame of the video as a base64-encoded image
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    filepath = Path(video_metadata[video_id]["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        hold_detector = HoldDetector()
        frame = hold_detector.get_first_frame(str(filepath))
        
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "frame": f"data:image/jpeg;base64,{frame_base64}",
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting first frame: {str(e)}")

@router.post("/detect-holds/{video_id}")
async def detect_holds_custom(
    video_id: str,
    request_data: dict = Body(...)
):
    """
    Detect holds with custom HSV thresholds
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    filepath = Path(video_metadata[video_id]["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        lower_hsv1 = request_data.get('lower_hsv1', [0, 100, 100])
        upper_hsv1 = request_data.get('upper_hsv1', [10, 255, 255])
        lower_hsv2 = request_data.get('lower_hsv2', [170, 100, 100])
        upper_hsv2 = request_data.get('upper_hsv2', [180, 255, 255])
        min_area = request_data.get('min_area', 100)
        roi = request_data.get('roi', None)  # Optional ROI: [x, y, width, height]
        
        hold_detector = HoldDetector()
        roi_tuple = tuple(roi) if roi and len(roi) == 4 else None
        holds = hold_detector.detect_holds(
            str(filepath),
            lower_hsv1=tuple(lower_hsv1),
            upper_hsv1=tuple(upper_hsv1),
            lower_hsv2=tuple(lower_hsv2),
            upper_hsv2=tuple(upper_hsv2),
            min_area=min_area,
            roi=roi_tuple
        )
        
        return {
            "holds": holds,
            "count": len(holds)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting holds: {str(e)}")

@router.post("/analyze/{video_id}")
async def analyze_video_with_holds(
    video_id: str,
    request_data: dict = Body(...)
):
    """
    Analyze a video with custom holds (can be from detection or manually added)
    """
    if video_id not in video_metadata:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already analyzed
    if video_id in analysis_results:
        return analysis_results[video_id]
    
    filepath = Path(video_metadata[video_id]["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        climber_weight = request_data.get('climber_weight', 70.0)
        custom_holds = request_data.get('custom_holds', None)
        finish_hold_index = request_data.get('finish_hold_index', None)  # Index of finish hold
        roi = request_data.get('roi', None)  # Optional ROI: [x, y, width, height]
        climber_point = request_data.get('climber_point', None)  # Optional point [x, y] for selecting climber
        climber_point_radius = request_data.get('climber_point_radius', 80.0)
        
        # Initialize components
        hold_detector = HoldDetector()
        pose_tracker = PoseTracker()
        analyzer = BiomechanicalAnalyzer(climber_weight=climber_weight)
        
        # Use custom holds if provided, otherwise detect automatically
        if custom_holds and len(custom_holds) > 0:
            holds = [tuple(h) for h in custom_holds]  # Convert to tuples
            print(f"Using {len(holds)} custom holds: {holds}")
        else:
            # Detect holds in first frame
            roi_tuple_for_holds = tuple(roi) if roi and len(roi) == 4 else None
            holds = hold_detector.detect_holds(str(filepath), roi=roi_tuple_for_holds)
            print(f"Detected {len(holds)} holds: {holds}")
        
        # Process video and track pose
        # Convert ROI to tuple if provided
        roi_tuple = tuple(roi) if roi and len(roi) == 4 else None
        if roi_tuple:
            print(f"Using ROI for pose detection: {roi_tuple}")

        climber_point_tuple = tuple(climber_point) if climber_point and len(climber_point) == 2 else None
        if climber_point_tuple:
            print(f"Using climber selection point: {climber_point_tuple} (radius={climber_point_radius}px)")

        frames_data, fps = pose_tracker.process_video(
            str(filepath),
            roi=roi_tuple,
            climber_point=climber_point_tuple,
            climber_radius=climber_point_radius
        )
        print(f"Processed {len(frames_data)} frames at {fps} fps")
        
        # Get video dimensions for coordinate conversion
        cap = cv2.VideoCapture(str(filepath))
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        print(f"Video dimensions: {video_width}x{video_height}")
        
        # Count frames with pose detection
        frames_with_pose = sum(1 for f in frames_data if f.get("has_pose", False))
        detection_rate = 100 * frames_with_pose / len(frames_data) if len(frames_data) > 0 else 0
        print(f"Frames with pose detected: {frames_with_pose}/{len(frames_data)} ({detection_rate:.1f}%)")
        
        # If pose detection is very low, warn user
        if detection_rate < 10 and len(frames_data) > 0:
            print(f"WARNING: Low pose detection rate ({detection_rate:.1f}%). Possible causes:")
            print("  - Escalador muy pequeño en el frame")
            print("  - Iluminación insuficiente")
            print("  - Escalador parcialmente fuera del frame")
            print("  - Considera usar ROI para enfocar en el área del escalador")
        
        # Perform biomechanical analysis
        result = analyzer.analyze(frames_data, holds, fps, video_id, roi=roi_tuple, finish_hold_index=finish_hold_index, video_width=video_width, video_height=video_height)
        print(f"Analysis complete. Result holds: {len(result.holds) if result.holds else 0}")
        if roi_tuple:
            print(f"ROI stored in result: {result.roi}")
        if finish_hold_index is not None:
            print(f"Finish hold index: {finish_hold_index} (hold {finish_hold_index + 1})")

        # Propagate climber radius so the overlay can draw the search zone
        result.climber_radius = float(climber_point_radius)

        # Store result
        analysis_results[video_id] = result

        return result

    except Exception as e:
        import traceback
        error_detail = f"Error analyzing video: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/videos")
async def list_videos():
    """List all uploaded videos"""
    return {
        "videos": [
            {
                "video_id": vid,
                "filename": meta["filename"],
                "uploaded_at": meta["uploaded_at"],
                "analyzed": vid in analysis_results
            }
            for vid, meta in video_metadata.items()
        ]
    }
