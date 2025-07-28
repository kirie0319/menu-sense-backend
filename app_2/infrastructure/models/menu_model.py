"""
Menu Model - Infrastructure Layer
SQLAlchemy model for menu data persistence
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app_2.core.database import Base
from app_2.domain.entities.menu_entity import MenuEntity


class MenuModel(Base):
    """
    メニューSQLAlchemyモデル
    
    純粋なメニューデータのみを管理
    セッション管理は分離済み
    """
    __tablename__ = "menus"

    # メニューID（UUID）
    id = Column(String, primary_key=True)
    
    # セッションID（外部キー）
    session_id = Column(String, ForeignKey('processing_sessions.session_id'), nullable=False, index=True)
    
    # 元言語の料理名
    name = Column(String, nullable=False)
    
    # 翻訳済み料理名（段階的更新対応でnullable）
    translation = Column(String, nullable=True)
    
    # 元言語のカテゴリー情報
    category = Column(String, nullable=True)
    
    # 翻訳済みカテゴリー情報
    category_translation = Column(String, nullable=True)
    
    # 価格情報
    price = Column(String, nullable=True)
    
    # GPT生成の詳細説明
    description = Column(Text, nullable=True)
    
    # アレルゲン情報
    allergy = Column(Text, nullable=True)
    
    # 主な含有成分
    ingredient = Column(Text, nullable=True)
    
    # Google画像検索結果
    search_engine = Column(String, nullable=True)
    
    # 生成画像URL
    gen_image = Column(String, nullable=True)

    # ========================================
    # タイムスタンプフィールド
    # ========================================
    
    # 作成日時
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    
    # 更新日時
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)

    # リレーション
    session = relationship("SessionModel", back_populates="menus")

    def to_entity(self) -> MenuEntity:
        """
        SQLAlchemyモデルをドメインエンティティに変換
        
        Returns:
            MenuEntity: ドメインエンティティ
        """
        return MenuEntity(
            id=self.id,
            name=self.name,
            translation=self.translation,
            category=self.category,
            category_translation=self.category_translation,
            price=self.price,
            description=self.description,
            allergy=self.allergy,
            ingredient=self.ingredient,
            search_engine=self.search_engine,
            gen_image=self.gen_image
        )

    @classmethod
    def from_entity_with_session(cls, entity: MenuEntity, session_id: str) -> "MenuModel":
        """
        ドメインエンティティからセッション付きSQLAlchemyモデルを作成
        
        Args:
            entity: ドメインエンティティ
            session_id: セッションID
            
        Returns:
            MenuModel: SQLAlchemyモデル
        """
        return cls(
            id=entity.id,
            session_id=session_id,
            name=entity.name,
            translation=entity.translation,
            category=entity.category,
            category_translation=entity.category_translation,
            price=entity.price,
            description=entity.description,
            allergy=entity.allergy,
            ingredient=entity.ingredient,
            search_engine=entity.search_engine,
            gen_image=entity.gen_image
        )

    def update_from_entity(self, entity: MenuEntity) -> None:
        """
        エンティティの内容でモデルを更新
        
        Args:
            entity: 更新内容のエンティティ
        """
        self.name = entity.name
        self.translation = entity.translation
        self.category = entity.category
        self.category_translation = entity.category_translation
        self.price = entity.price
        self.description = entity.description
        self.allergy = entity.allergy
        self.ingredient = entity.ingredient
        self.search_engine = entity.search_engine
        self.gen_image = entity.gen_image
        self.updated_at = datetime.utcnow()
