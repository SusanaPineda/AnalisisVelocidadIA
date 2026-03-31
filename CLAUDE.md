# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend (from project root):**
```bash
# Install dependencies (Python 3.8+)
pip install -r requirements.txt

# Run backend
cd backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# or use the helper script:
./start_backend.sh          # WSL/Linux
start_backend.bat           # Windows

# Check dependencies
python verify_installation.py
```

**Frontend:**
```bash
cd frontend && python3 -m http.server 8080
# Then open http://localhost:8080 (or open frontend/index.html directly)
```

**API docs:** http://localhost:8000/docs (Swagger), http://localhost:8000/redoc

There are no automated tests or lint commands in this project.

## Architecture

The system analyzes climbing videos biomechanically. The frontend is plain HTML/JS; the backend is FastAPI. All state (uploaded videos, analysis results) is stored **in-memory** — restart clears everything.

### Analysis pipeline

```
Upload video → POST /api/upload → returns video_id (UUID)
     ↓
Detect holds → POST /api/detect-holds/{video_id}   (HSV color thresholding)
     ↓
User confirms/edits holds on frontend canvas
     ↓
Analyze → POST /api/analyze/{video_id}             (pose + biomechanics)
     ↓
Generate overlay → GET /api/overlay/{video_id}     (skeleton drawn on video)
```

The analyze endpoint accepts: `custom_holds`, `roi`, `climber_point`, `climber_point_radius`, `finish_hold_index`, `climber_weight`.

### Coordinate systems

Three systems are used — always be explicit about which one:

| System | Range | Used for |
|--------|-------|----------|
| **Original pixel** | `(0,0)` top-left, full frame size | Hold coordinates, ROI |
| **Normalized** | `0–1` relative to full frame | Stored landmarks, distance filtering |
| **MediaPipe** | `0–1` relative to *processed* frame (after ROI crop + resize) | Raw MediaPipe output only |

`PoseTracker` converts MediaPipe → pixel → normalized in four steps (see `pose_tracker.py:131–152`). Hold coordinates are always in original pixel space.

### Climber tracking / multi-person disambiguation

`PoseTracker.process_video()` accepts an optional `climber_point (x, y)` and `climber_radius`. It filters MediaPipe poses by computing the shoulder+hip center (landmarks 11,12,23,24) and rejecting poses whose center is farther than `climber_radius` from the **last accepted pose center** (`current_climber_norm`). This center updates each frame so the zone follows the climber up the wall.

If no `climber_point` is provided, no filtering is applied — all detected poses are accepted.

### Hold detection

Uses HSV thresholding for red holds. Red wraps in HSV space, so two ranges are combined:
- Range 1: H=[0–10], Range 2: H=[170–180], both with S=[100–255], V=[100–255].
The defaults are configurable; the frontend also supports eyedropper color picking to auto-generate thresholds.

### Video overlay

`VideoOverlay.create_overlay()` draws:
- MediaPipe skeleton (from stored landmarks, not re-running MediaPipe)
- Centre of Mass (green dot)
- Climber search zone (orange semi-transparent circle, 10% opacity) around torso when pose is detected
- Hold circles (red = untouched, green = touched, purple = finish hold)
- If `analysis_result.roi` is set, output video is **cropped** to that ROI region

Overlay tries `mp4v` codec first, falls back to `XVID`/`MJPG` in AVI, then optionally re-encodes with `ffmpeg` (H.264) if available.

### Key files

| File | Responsibility |
|------|---------------|
| `backend/app/api/routes.py` | All endpoints; orchestrates the pipeline |
| `backend/app/services/vision/pose_tracker.py` | MediaPipe pose extraction, ROI crop, dynamic climber zone |
| `backend/app/services/vision/hold_detector.py` | HSV contour detection; returns holds in pixel coords |
| `backend/app/services/vision/video_overlay.py` | Draws skeleton + holds + CoM + search zone onto video |
| `backend/app/services/biomechanics/analyzer.py` | CoM, velocity, acceleration, forces, step detection |
| `backend/app/models/schemas.py` | All Pydantic request/response models |
| `backend/app/core/config.py` | Thresholds (confidence 0.3, smoothing window 5 frames, max upload 100 MB) |
| `frontend/app.js` | All UI logic: ROI drawing, hold editing, climber picker, chart rendering |
