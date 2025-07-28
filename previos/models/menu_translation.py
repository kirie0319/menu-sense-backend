"""
SQLAlchemy models for Menu Translation Database

This module defines the database schema for storing menu translation results
including sessions, menu items, processing providers, and images.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime

class Session(Base):
    """
    Session model for tracking menu translation sessions
    
    Each session represents a complete menu translation workflow
    from OCR extraction to final image generation.
    """
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    total_items = Column(Integer, nullable=False)
    status = Column(String(20), default='processing')  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    session_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_items = relationship("MenuItem", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', status='{self.status}', total_items={self.total_items})>"

class MenuItem(Base):
    """
    MenuItem model for individual menu items within a session
    
    Stores the core translation data: Japanese text, English translation,
    category, description, and processing status.
    """
    __tablename__ = "menu_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    japanese_text = Column(Text, nullable=False)
    english_text = Column(Text)
    category = Column(String(100))
    description = Column(Text)
    
    # Status tracking for each processing stage
    translation_status = Column(String(20), default='pending')  # pending, completed, failed
    description_status = Column(String(20), default='pending')
    image_status = Column(String(20), default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="menu_items")
    providers = relationship("ProcessingProvider", back_populates="menu_item", cascade="all, delete-orphan")
    images = relationship("MenuItemImage", back_populates="menu_item", cascade="all, delete-orphan")
    
    # Composite unique constraint on session_id and item_id
    __table_args__ = (
        UniqueConstraint('session_id', 'item_id', name='uq_session_item'),
    )

    def __repr__(self):
        return f"<MenuItem(id={self.item_id}, japanese='{self.japanese_text[:20]}...', english='{self.english_text[:20] if self.english_text else 'None'}...')>"

class ProcessingProvider(Base):
    """
    ProcessingProvider model for tracking which AI services processed each stage
    
    Records which provider (Google Translate, OpenAI, etc.) was used for each
    processing stage along with metadata like processing time and fallback usage.
    """
    __tablename__ = "processing_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.id'), nullable=False)
    stage = Column(String(20), nullable=False)  # translation, description, image
    provider = Column(String(100), nullable=False)  # e.g., "Google Translate API", "OpenAI GPT-4.1-mini"
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Integer)  # Processing time in milliseconds
    fallback_used = Column(Boolean, default=False)
    provider_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="providers")

    def __repr__(self):
        return f"<ProcessingProvider(stage='{self.stage}', provider='{self.provider}', fallback={self.fallback_used})>"

class MenuItemImage(Base):
    """
    MenuItemImage model for storing generated images
    
    Stores image URLs, S3 keys, generation prompts, and metadata
    for AI-generated food images.
    """
    __tablename__ = "menu_item_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.id'), nullable=False)
    image_url = Column(Text, nullable=False)
    s3_key = Column(Text)  # S3 object key for the image
    prompt = Column(Text)  # The prompt used to generate the image
    provider = Column(String(100))  # e.g., "Google Imagen 3"
    fallback_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="images")

    def __repr__(self):
        return f"<MenuItemImage(provider='{self.provider}', fallback={self.fallback_used})>"

class Category(Base):
    """
    Category model for menu item categories
    
    Normalized table for menu categories like Appetizers, Main Dishes, etc.
    """
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category(name='{self.name}')>"