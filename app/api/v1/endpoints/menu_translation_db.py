"""
Database-Integrated Menu Translation API Endpoints

These endpoints provide database-backed operations for menu translation,
offering enhanced querying, analytics, and data persistence capabilities.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import time

from app.core.database import get_db_session
from app.repositories.menu_translation_repository import MenuTranslationRepository, SessionProgress
from app.services.menu_translation_service import MenuTranslationService
from app.models.menu_translation import Session, MenuItem

router = APIRouter()

# ===============================================
# 📋 Request/Response Models
# ===============================================

class CreateSessionRequest(BaseModel):
    """Request model for creating a new session"""
    session_id: str
    menu_items: List[str]
    metadata: Optional[Dict[str, Any]] = None

class CreateSessionResponse(BaseModel):
    """Response model for session creation"""
    success: bool
    session_id: str
    total_items: int
    status: str
    created_at: datetime
    database_id: str
    message: str

class SessionProgressResponse(BaseModel):
    """Response model for session progress"""
    session_id: str
    total_items: int
    translation_completed: int
    description_completed: int
    image_completed: int
    fully_completed: int
    progress_percentage: float
    last_updated: datetime

class MenuItemResponse(BaseModel):
    """Response model for menu item data"""
    session_id: str
    item_id: int
    japanese_text: str
    english_text: Optional[str]
    category: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    translation_status: str
    description_status: str
    image_status: str
    providers: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

class SessionDetailResponse(BaseModel):
    """Response model for complete session data"""
    session_id: str
    total_items: int
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]
    menu_items: List[MenuItemResponse]
    progress: SessionProgressResponse

class SearchRequest(BaseModel):
    """Request model for search"""
    query: str
    category: Optional[str] = None
    limit: int = 10
    page: int = 1

class SearchResponse(BaseModel):
    """Response model for search results"""
    query: str
    category: Optional[str]
    total_results: int
    results: List[MenuItemResponse]
    pagination: Dict[str, int]

class MigrateRequest(BaseModel):
    """Request model for Redis migration"""
    item_count: int
    force_migration: bool = False

class MigrateResponse(BaseModel):
    """Response model for migration results"""
    success: bool
    session_id: str
    migrated_items: int
    migration_time: float
    message: str

class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics"""
    total_sessions: int
    total_menu_items: int
    completed_sessions: int
    processing_sessions: int
    failed_sessions: int
    average_items_per_session: float
    most_common_categories: List[Dict[str, Any]]
    database_size_info: Dict[str, Any]
    last_updated: datetime

# ===============================================
# 🛠️ Dependencies
# ===============================================

async def get_menu_translation_service(db_session = Depends(get_db_session)) -> MenuTranslationService:
    """Dependency to get MenuTranslationService with database session"""
    repository = MenuTranslationRepository(db_session)
    # TODO: Add Redis client here when needed for backward compatibility
    return MenuTranslationService(repository, redis_client=None)

# ===============================================
# 🔄 Session Management Endpoints
# ===============================================

@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_translation_session(
    request: CreateSessionRequest,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Create a new menu translation session with database storage
    
    This endpoint creates a new session and stores it in the database,
    providing enhanced data persistence and querying capabilities.
    """
    try:
        session = await service.start_translation_session(
            session_id=request.session_id,
            menu_items=request.menu_items,
            metadata=request.metadata
        )
        
        return CreateSessionResponse(
            success=True,
            session_id=session.session_id,
            total_items=session.total_items,
            status=session.status,
            created_at=session.created_at,
            database_id=str(session.id),
            message=f"Session created successfully with {session.total_items} menu items"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_with_items(
    session_id: str,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Get complete session data with all menu items and processing details
    
    Returns comprehensive session information including all menu items,
    their processing status, providers used, and generated content.
    """
    try:
        session = await service.get_session_with_items(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get progress
        progress = await service.get_real_time_progress(session_id)
        
        # Format menu items
        menu_items = []
        for item in session.menu_items:
            # Get image URL from images relationship
            image_url = None
            if item.images:
                image_url = item.images[0].image_url
            
            # Format providers
            providers = [
                {
                    "stage": provider.stage,
                    "provider": provider.provider,
                    "processing_time_ms": provider.processing_time_ms,
                    "fallback_used": provider.fallback_used,
                    "processed_at": provider.processed_at
                }
                for provider in item.providers
            ]
            
            menu_items.append(MenuItemResponse(
                session_id=session.session_id,
                item_id=item.item_id,
                japanese_text=item.japanese_text,
                english_text=item.english_text,
                category=item.category,
                description=item.description,
                image_url=image_url,
                translation_status=item.translation_status,
                description_status=item.description_status,
                image_status=item.image_status,
                providers=providers,
                created_at=item.created_at,
                updated_at=item.updated_at
            ))
        
        return SessionDetailResponse(
            session_id=session.session_id,
            total_items=session.total_items,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            completed_at=session.completed_at,
            metadata=session.session_metadata,
            menu_items=menu_items,
            progress=SessionProgressResponse(
                session_id=session_id,
                total_items=progress.total_items,
                translation_completed=progress.translation_completed,
                description_completed=progress.description_completed,
                image_completed=progress.image_completed,
                fully_completed=progress.fully_completed,
                progress_percentage=progress.progress_percentage,
                last_updated=datetime.utcnow()
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.get("/sessions/{session_id}/progress", response_model=SessionProgressResponse)
async def get_session_progress(
    session_id: str,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Get real-time session progress from database
    
    Provides accurate, up-to-date progress information by querying
    the database directly rather than relying on Redis cache.
    """
    try:
        progress = await service.get_real_time_progress(session_id)
        
        return SessionProgressResponse(
            session_id=session_id,
            total_items=progress.total_items,
            translation_completed=progress.translation_completed,
            description_completed=progress.description_completed,
            image_completed=progress.image_completed,
            fully_completed=progress.fully_completed,
            progress_percentage=progress.progress_percentage,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Mark session as completed
    
    Updates the session status to 'completed' and sets the completion timestamp.
    """
    try:
        session = await service.complete_session(session_id)
        
        return {
            "success": True,
            "session_id": session.session_id,
            "status": session.status,
            "completed_at": session.completed_at,
            "message": f"Session {session_id} marked as completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete session: {str(e)}")

# ===============================================
# 🔍 Search and Query Endpoints  
# ===============================================

@router.get("/search", response_model=SearchResponse)
async def search_menu_items(
    query: str = Query(..., description="Search query text"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Search menu items across all sessions
    
    Performs full-text search across Japanese text, English translations,
    and descriptions. Results can be filtered by category and paginated.
    """
    try:
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Perform search
        results = await service.search_menu_items(query, category, limit + offset)
        
        # Apply pagination
        paginated_results = results[offset:offset + limit]
        
        # Format results
        formatted_results = []
        for item in paginated_results:
            # Get image URL
            image_url = None
            if item.images:
                image_url = item.images[0].image_url
            
            # Format providers
            providers = [
                {
                    "stage": provider.stage,
                    "provider": provider.provider,
                    "fallback_used": provider.fallback_used
                }
                for provider in item.providers
            ]
            
            formatted_results.append(MenuItemResponse(
                session_id=item.session.session_id,
                item_id=item.item_id,
                japanese_text=item.japanese_text,
                english_text=item.english_text,
                category=item.category,
                description=item.description,
                image_url=image_url,
                translation_status=item.translation_status,
                description_status=item.description_status,
                image_status=item.image_status,
                providers=providers,
                created_at=item.created_at,
                updated_at=item.updated_at
            ))
        
        # Calculate pagination info
        total_results = len(results)
        total_pages = (total_results + limit - 1) // limit
        
        return SearchResponse(
            query=query,
            category=category,
            total_results=total_results,
            results=formatted_results,
            pagination={
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_results": total_results
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# ===============================================
# 🔄 Migration and Utilities
# ===============================================

@router.post("/migrate/{session_id}", response_model=MigrateResponse)
async def migrate_redis_to_database(
    session_id: str,
    request: MigrateRequest,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Migrate existing Redis data to database
    
    Attempts to migrate session data from Redis to the database.
    Useful for transitioning from the old Redis-based system.
    """
    try:
        start_time = time.time()
        
        session = await service.migrate_from_redis(session_id, request.item_count)
        
        migration_time = time.time() - start_time
        
        if not session:
            raise HTTPException(
                status_code=404, 
                detail=f"No Redis data found for session {session_id} or session already exists in database"
            )
        
        return MigrateResponse(
            success=True,
            session_id=session.session_id,
            migrated_items=session.total_items,
            migration_time=migration_time,
            message=f"Successfully migrated {session.total_items} items from Redis to database"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_statistics(
    db_session = Depends(get_db_session)
):
    """
    Get database statistics and analytics
    
    Provides comprehensive statistics about the menu translation database
    including session counts, item counts, and category distributions.
    """
    try:
        repository = MenuTranslationRepository(db_session)
        
        # TODO: Implement statistics calculation in repository
        # For now, return mock data to satisfy the interface
        
        return DatabaseStatsResponse(
            total_sessions=0,
            total_menu_items=0,
            completed_sessions=0,
            processing_sessions=0,
            failed_sessions=0,
            average_items_per_session=0.0,
            most_common_categories=[],
            database_size_info={"estimated_size_mb": 0},
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

# ===============================================
# 🔍 Individual Item Endpoints
# ===============================================

@router.get("/sessions/{session_id}/items/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    session_id: str,
    item_id: int,
    service: MenuTranslationService = Depends(get_menu_translation_service)
):
    """
    Get specific menu item with full details
    
    Returns detailed information about a specific menu item including
    all processing stages, providers used, and generated content.
    """
    try:
        # Get the item through repository
        repository = service.repository
        menu_item = await repository.get_menu_item_by_id(session_id, item_id)
        
        if not menu_item:
            raise HTTPException(
                status_code=404, 
                detail=f"Menu item {item_id} not found in session {session_id}"
            )
        
        # Get image URL
        image_url = None
        if menu_item.images:
            image_url = menu_item.images[0].image_url
        
        # Format providers
        providers = [
            {
                "stage": provider.stage,
                "provider": provider.provider,
                "processing_time_ms": provider.processing_time_ms,
                "fallback_used": provider.fallback_used,
                "processed_at": provider.processed_at,
                "metadata": provider.provider_metadata
            }
            for provider in menu_item.providers
        ]
        
        return MenuItemResponse(
            session_id=session_id,
            item_id=menu_item.item_id,
            japanese_text=menu_item.japanese_text,
            english_text=menu_item.english_text,
            category=menu_item.category,
            description=menu_item.description,
            image_url=image_url,
            translation_status=menu_item.translation_status,
            description_status=menu_item.description_status,
            image_status=menu_item.image_status,
            providers=providers,
            created_at=menu_item.created_at,
            updated_at=menu_item.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get menu item: {str(e)}")