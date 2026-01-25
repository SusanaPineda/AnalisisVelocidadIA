"""
FastAPI application entry point for Speed Climbing Biomechanical Analysis System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api import routes
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="Speed Climbing Biomechanical Analysis API",
    description="API for analyzing speed climbing performance using computer vision and biomechanics",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api", tags=["analysis"])

# Serve static files (processed videos)
# Use settings.PROCESSED_DIR for consistency
settings.PROCESSED_DIR.mkdir(exist_ok=True)
app.mount("/processed", StaticFiles(directory=str(settings.PROCESSED_DIR)), name="processed")

@app.get("/")
async def root():
    return {"message": "Speed Climbing Biomechanical Analysis API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
