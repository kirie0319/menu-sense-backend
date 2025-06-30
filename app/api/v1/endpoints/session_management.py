"""
Session Management API endpoints for monitoring and managing JSON storage sessions.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class SessionHealthResponse(BaseModel):
    """Response model for session health check"""
    total_sessions: int
    status_distribution: Dict[str, int]
    stale_sessions: List[Dict[str, Any]]
    health_check_timestamp: str

class SessionCleanupResponse(BaseModel):
    """Response model for session cleanup"""
    cleaned_sessions: int
    cleanup_timestamp: str
    message: str

class SessionRecoveryResponse(BaseModel):
    """Response model for session recovery"""
    success: bool
    session_id: str
    message: str

@router.get("/health", response_model=SessionHealthResponse)
async def get_session_health():
    """
    Get comprehensive health report of all sessions
    """
    try:
        health_report = enhanced_json_storage.get_session_health_report()
        
        if "error" in health_report:
            raise HTTPException(status_code=500, detail=health_report["error"])
        
        return SessionHealthResponse(**health_report)
        
    except Exception as e:
        logger.error(f"Failed to get session health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session health: {str(e)}")

@router.post("/cleanup", response_model=SessionCleanupResponse)
async def cleanup_stale_sessions(
    max_age_hours: int = Query(2, description="Maximum age in hours for sessions to be considered stale")
):
    """
    Clean up stale sessions that haven't been updated within the specified time
    """
    try:
        if max_age_hours < 1 or max_age_hours > 24:
            raise HTTPException(status_code=400, detail="max_age_hours must be between 1 and 24")
        
        cleaned_count = enhanced_json_storage.cleanup_stale_sessions(max_age_hours)
        
        return SessionCleanupResponse(
            cleaned_sessions=cleaned_count,
            cleanup_timestamp=enhanced_json_storage._ensure_base_directory(),
            message=f"Successfully cleaned up {cleaned_count} stale sessions"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup stale sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup stale sessions: {str(e)}")

@router.post("/recover/{session_id}", response_model=SessionRecoveryResponse)
async def recover_session(session_id: str):
    """
    Attempt to recover a failed or stale session
    """
    try:
        success = enhanced_json_storage.recover_session(session_id)
        
        if success:
            return SessionRecoveryResponse(
                success=True,
                session_id=session_id,
                message=f"Session {session_id} recovery initiated successfully"
            )
        else:
            return SessionRecoveryResponse(
                success=False,
                session_id=session_id,
                message=f"Failed to recover session {session_id} - session may not exist or already be healthy"
            )
            
    except Exception as e:
        logger.error(f"Failed to recover session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to recover session: {str(e)}")

@router.get("/status/{session_id}")
async def get_session_status(session_id: str):
    """
    Get current status of a specific session
    """
    try:
        # Get status from memory
        memory_status = enhanced_json_storage.get_session_status(session_id)
        
        # Get status from file
        file_data = enhanced_json_storage.load_menu_translation(session_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        file_status = file_data.get("status", "unknown")
        
        return {
            "session_id": session_id,
            "file_status": file_status,
            "memory_status": memory_status,
            "total_items": file_data.get("total_items", 0),
            "completed_items": len([
                item for item in file_data.get("menu_items", [])
                if item.get("description") and item.get("image_url")
            ]),
            "last_updated": file_data.get("last_updated"),
            "processing_progress": enhanced_json_storage._determine_session_status(file_data.get("menu_items", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

@router.get("/list")
async def list_sessions(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD format)"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List all sessions with optional filtering
    """
    try:
        sessions = enhanced_json_storage.list_translations(date)
        
        # Add status information to each session
        enhanced_sessions = []
        for session in sessions:
            session_data = enhanced_json_storage.load_menu_translation(session["session_id"])
            if session_data:
                session["status"] = session_data.get("status", "unknown")
                session["total_items"] = session_data.get("total_items", 0)
                session["completed_items"] = len([
                    item for item in session_data.get("menu_items", [])
                    if item.get("description") and item.get("image_url")
                ])
                
                # Apply status filter if provided
                if not status or session["status"] == status:
                    enhanced_sessions.append(session)
        
        return {
            "sessions": enhanced_sessions,
            "total_count": len(enhanced_sessions),
            "filters_applied": {
                "date": date,
                "status": status
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.delete("/delete/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and its associated data
    """
    try:
        file_path = enhanced_json_storage._get_file_path(session_id)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Remove from memory tracking
        with enhanced_json_storage._status_lock:
            if session_id in enhanced_json_storage._session_status:
                del enhanced_json_storage._session_status[session_id]
        
        # Delete file
        file_path.unlink()
        
        logger.info(f"Session {session_id} deleted successfully")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session {session_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.get("/stale")
async def detect_stale_sessions(
    max_age_hours: int = Query(2, description="Maximum age in hours for sessions to be considered stale")
):
    """
    Detect and return list of stale sessions without cleaning them up
    """
    try:
        if max_age_hours < 1 or max_age_hours > 24:
            raise HTTPException(status_code=400, detail="max_age_hours must be between 1 and 24")
        
        stale_sessions = enhanced_json_storage.detect_stale_sessions(max_age_hours)
        
        return {
            "stale_sessions": stale_sessions,
            "count": len(stale_sessions),
            "max_age_hours": max_age_hours,
            "check_timestamp": enhanced_json_storage._ensure_base_directory()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect stale sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect stale sessions: {str(e)}")