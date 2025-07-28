# 🏗️ Infrastructure First 実装ガイド

## 📋 概要

**目的**: リアルタイム処理システムを効率的かつ安全に実装するための段階的ガイド  
**アプローチ**: Infrastructure First - 基盤から順次構築  
**実装期間**: 4週間（各Phase 1週間）  
**設計原則**: 依存関係の自然な流れに沿った実装順序

---

## 🎯 Infrastructure First アプローチの利点

### **なぜInfrastructure Firstが最適か**

#### **1. 依存関係の自然な順序**
```
Infrastructure Layer (基盤)
    ↓ 依存
Service Layer (ビジネスロジック)
    ↓ 依存  
Pipeline Layer (フロー制御)
    ↓ 依存
API Layer (HTTP境界)
```

#### **2. 早期テスト・検証可能性**
- ✅ 各段階で実際のDB・Redisを使用したテスト
- ✅ モック不要の統合テスト
- ✅ 問題の早期発見・修正

#### **3. 実装ブロッカーの回避**
- ✅ 上位レイヤー実装時に基盤が確実に動作
- ✅ 依存関係による開発停止を防止
- ✅ 並列開発の可能性

---

## 🗓️ 実装スケジュール概要

| Week | Phase | 実装レイヤー | 主要成果物 |
|------|-------|-------------|------------|
| **Week 1** | Infrastructure | DB + Redis + Core | 確実な基盤構築 |
| **Week 2** | Service & Domain | ビジネスロジック + イベント | 処理ロジック完成 |
| **Week 3** | Pipeline & Task | フロー制御 + 並列処理 | 実行エンジン完成 |
| **Week 4** | API & Integration | HTTP境界 + SSE | システム統合完成 |

---

## 📊 Phase 1: Infrastructure Layer (Week 1)

### **🎯 Phase 1の目標**
- データ永続化基盤の完成
- リアルタイム通信基盤の完成
- 設定管理の完成
- 基盤レイヤーの完全テスト

### **Step 1-1: Database Model 拡張 (Day 1-2)**

#### **ファイル**: `infrastructure/models/menu_model.py`

```python
from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime

class MenuModel(Base):
    """メニューモデル（リアルタイム処理対応拡張）"""
    __tablename__ = "menus"
    
    # 既存フィールド
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    translation = Column(String, nullable=True)
    category = Column(String, nullable=True)
    category_translation = Column(String, nullable=True)
    price = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    allergy = Column(Text, nullable=True)
    ingredient = Column(Text, nullable=True)
    search_engine = Column(String, nullable=True)
    gen_image = Column(String, nullable=True)
    
    # 🆕 リアルタイム処理対応フィールド
    session_id = Column(String, nullable=False, index=True)  # セッション管理
    processing_status = Column(String, default="pending")   # pending/processing/completed/failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 🆕 8並列処理対応フィールド  
    task6_data = Column(Text, nullable=True)  # 追加処理1の結果
    task7_data = Column(Text, nullable=True)  # 追加処理2の結果
    task8_data = Column(Text, nullable=True)  # 追加処理3の結果
    
    @classmethod
    def from_entity_with_session(cls, entity: MenuEntity, session_id: str) -> "MenuModel":
        """セッションID付きでEntityからモデル作成"""
        model = cls.from_entity(entity)
        model.session_id = session_id
        model.processing_status = "basic_completed"
        return model
    
    def update_processing_status(self, status: str):
        """処理ステータス更新"""
        self.processing_status = status
        self.updated_at = datetime.utcnow()
```

#### **検証方法**
```python
# tests/infrastructure/test_menu_model.py
@pytest.mark.asyncio
async def test_menu_model_extensions():
    # セッションID付き作成テスト
    entity = MenuEntity(id="test", name="test", translation="test")
    model = MenuModel.from_entity_with_session(entity, "session-123")
    
    assert model.session_id == "session-123"
    assert model.processing_status == "basic_completed"
    assert model.created_at is not None
```

### **Step 1-2: Repository 拡張 (Day 2-3)**

#### **ファイル**: `infrastructure/repositories/menu_repository_impl.py`

```python
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

class MenuRepositoryImpl(MenuRepositoryInterface):
    """メニューリポジトリ（リアルタイム処理対応拡張）"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # 🆕 セッション関連メソッド
    async def save_with_session(self, menu: MenuEntity, session_id: str) -> MenuEntity:
        """セッションID付きでメニューを保存"""
        try:
            menu_model = MenuModel.from_entity_with_session(menu, session_id)
            
            self.session.add(menu_model)
            await self.session.commit()
            await self.session.refresh(menu_model)
            
            logger.info(f"Menu saved with session: {menu.id} -> {session_id}")
            return menu_model.to_entity()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save menu with session {menu.id}: {e}")
            raise
    
    async def get_by_session_id(self, session_id: str) -> List[MenuEntity]:
        """セッションIDでメニュー一覧取得"""
        try:
            stmt = select(MenuModel).where(MenuModel.session_id == session_id)
            result = await self.session.execute(stmt)
            menu_models = result.scalars().all()
            
            return [model.to_entity() for model in menu_models]
            
        except Exception as e:
            logger.error(f"Failed to get menus by session {session_id}: {e}")
            raise
    
    async def update_processing_status(self, menu_id: str, status: str) -> None:
        """処理ステータス更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                processing_status=status,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update status for menu {menu_id}: {e}")
            raise
    
    # 🆕 段階的更新メソッド群
    async def update_translation(self, menu_id: str, translation: str) -> MenuEntity:
        """翻訳結果を更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                translation=translation,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
            return await self.get_by_id(menu_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update translation for menu {menu_id}: {e}")
            raise
    
    async def update_description(self, menu_id: str, description: str) -> MenuEntity:
        """説明を更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                description=description,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
            return await self.get_by_id(menu_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update description for menu {menu_id}: {e}")
            raise
    
    async def update_allergen(self, menu_id: str, allergen: str) -> MenuEntity:
        """アレルゲン情報を更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                allergy=allergen,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
            return await self.get_by_id(menu_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update allergen for menu {menu_id}: {e}")
            raise
    
    async def update_ingredient(self, menu_id: str, ingredient: str) -> MenuEntity:
        """成分情報を更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                ingredient=ingredient,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
            return await self.get_by_id(menu_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update ingredient for menu {menu_id}: {e}")
            raise
    
    async def update_search_engine(self, menu_id: str, search_result: str) -> MenuEntity:
        """画像検索結果を更新"""
        try:
            stmt = update(MenuModel).where(MenuModel.id == menu_id).values(
                search_engine=search_result,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
            return await self.get_by_id(menu_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update search result for menu {menu_id}: {e}")
            raise
    
    # 🆕 バッチ処理用メソッド
    async def batch_save_with_session(
        self, 
        menus: List[MenuEntity], 
        session_id: str
    ) -> List[MenuEntity]:
        """バッチ処理でのメニュー保存"""
        try:
            menu_models = [
                MenuModel.from_entity_with_session(menu, session_id) 
                for menu in menus
            ]
            
            self.session.add_all(menu_models)
            await self.session.commit()
            
            # 一括でリフレッシュ
            for model in menu_models:
                await self.session.refresh(model)
            
            logger.info(f"Batch saved {len(menu_models)} menus with session: {session_id}")
            return [model.to_entity() for model in menu_models]
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to batch save menus for session {session_id}: {e}")
            raise
```

#### **検証方法**
```python
# tests/infrastructure/test_menu_repository.py
@pytest.mark.asyncio
async def test_session_operations():
    repository = MenuRepositoryImpl(db_session)
    
    # セッション保存テスト
    menu = MenuEntity(id="test", name="test", translation="test")
    saved = await repository.save_with_session(menu, "session-123")
    
    # セッション取得テスト
    menus = await repository.get_by_session_id("session-123")
    assert len(menus) == 1
    assert menus[0].id == "test"
    
    # 段階的更新テスト
    updated = await repository.update_translation("test", "テスト")
    assert updated.translation == "テスト"
```

### **Step 1-3: Redis Infrastructure (Day 3-4)**

#### **ファイル**: `infrastructure/redis/publisher.py`

```python
import json
import redis.asyncio as redis
from typing import Dict, Any
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("redis_publisher")

class RedisPublisher:
    """Redis Pub/Sub Publisher"""
    
    def __init__(self):
        self.redis_url = settings.celery.redis_url
        self._connection = None
    
    async def get_connection(self) -> redis.Redis:
        """Redis接続取得（再利用）"""
        if self._connection is None or self._connection.closed:
            self._connection = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self._connection
    
    async def publish(self, channel: str, message: str) -> bool:
        """メッセージ配信"""
        try:
            redis_client = await self.get_connection()
            result = await redis_client.publish(channel, message)
            
            logger.debug(f"Published to {channel}: {len(message)} bytes, {result} subscribers")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False
    
    async def publish_json(self, channel: str, data: Dict[str, Any]) -> bool:
        """JSON形式でメッセージ配信"""
        try:
            message = json.dumps(data, ensure_ascii=False)
            return await self.publish(channel, message)
            
        except Exception as e:
            logger.error(f"Failed to publish JSON to {channel}: {e}")
            return False
    
    async def create_sse_channel(self, session_id: str) -> str:
        """SSE用チャンネル名生成"""
        return f"{settings.sse.redis_channel_prefix}:{session_id}"
    
    async def close(self):
        """接続クローズ"""
        if self._connection and not self._connection.closed:
            await self._connection.close()
```

#### **ファイル**: `infrastructure/redis/subscriber.py`

```python
import json
import asyncio
from typing import AsyncIterator, Dict, Any, Optional
import redis.asyncio as redis
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("redis_subscriber")

class RedisSubscriber:
    """Redis Pub/Sub Subscriber"""
    
    def __init__(self):
        self.redis_url = settings.celery.redis_url
        self._pubsub = None
        self._connection = None
    
    async def get_connection(self) -> redis.Redis:
        """Redis接続取得"""
        if self._connection is None or self._connection.closed:
            self._connection = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self._connection
    
    async def subscribe(self, channel: str) -> bool:
        """チャンネル購読開始"""
        try:
            redis_client = await self.get_connection()
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(channel)
            
            logger.info(f"Subscribed to channel: {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False
    
    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        """メッセージ受信ジェネレーター"""
        if not self._pubsub:
            raise RuntimeError("Not subscribed to any channel")
        
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        # JSON形式の場合はパース
                        if message["data"].startswith("{"):
                            yield json.loads(message["data"])
                        else:
                            yield {"raw_message": message["data"]}
                            
                    except json.JSONDecodeError:
                        yield {"raw_message": message["data"]}
                        
        except Exception as e:
            logger.error(f"Error in message listening: {e}")
            raise
    
    async def unsubscribe(self, channel: str):
        """チャンネル購読停止"""
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from channel: {channel}")
    
    async def close(self):
        """接続クローズ"""
        if self._pubsub:
            await self._pubsub.close()
        if self._connection and not self._connection.closed:
            await self._connection.close()
```

#### **検証方法**
```python
# tests/infrastructure/test_redis.py
@pytest.mark.asyncio
async def test_redis_pubsub():
    publisher = RedisPublisher()
    subscriber = RedisSubscriber()
    
    # 購読開始
    await subscriber.subscribe("test-channel")
    
    # メッセージ配信
    test_data = {"type": "test", "message": "hello"}
    success = await publisher.publish_json("test-channel", test_data)
    assert success
    
    # メッセージ受信
    async for message in subscriber.listen():
        assert message["type"] == "test"
        assert message["message"] == "hello"
        break
    
    await subscriber.close()
    await publisher.close()
```

### **Step 1-4: Core Configuration 拡張 (Day 4-5)**

#### **ファイル**: `core/config.py`

```python
class SSESettings(BaseModel):
    """SSE関連設定"""
    max_connections: int = 1000
    keepalive_interval: int = 30  # seconds
    event_history_ttl: int = 3600  # 1 hour
    max_event_size: int = 1024 * 1024  # 1MB
    redis_channel_prefix: str = "sse"
    reconnect_interval: int = 5  # seconds
    max_reconnect_attempts: int = 3

class ProcessingSettings(BaseModel):
    """処理関連設定"""
    max_parallel_tasks: int = 8
    task_timeout: int = 300  # 5 minutes
    retry_attempts: int = 3
    retry_delay: int = 60  # 1 minute
    session_ttl: int = 3600  # 1 hour
    batch_size: int = 100  # バッチ処理サイズ
    progress_update_interval: int = 10  # seconds

class DatabaseSettings(BaseModel):
    """データベース関連設定"""
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo_sql: bool = False

# Settings class に追加
class Settings:
    # ... existing settings ...
    sse: SSESettings = SSESettings()
    processing: ProcessingSettings = ProcessingSettings()
    database: DatabaseSettings = DatabaseSettings()
```

#### **ファイル**: `core/redis_client.py` (拡張)

```python
from functools import lru_cache
import redis.asyncio as redis
from app_2.infrastructure.redis.publisher import RedisPublisher
from app_2.infrastructure.redis.subscriber import RedisSubscriber

@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Redis クライアント取得（既存）"""
    return redis.from_url(settings.celery.redis_url, decode_responses=True)

@lru_cache(maxsize=1)
def get_redis_publisher() -> RedisPublisher:
    """Redis Publisher 取得（新規）"""
    return RedisPublisher()

def get_redis_subscriber() -> RedisSubscriber:
    """Redis Subscriber 取得（新規）"""
    # Subscriberはステートフルなので、毎回新しいインスタンスを作成
    return RedisSubscriber()
```

### **Step 1-5: Phase 1 統合テスト (Day 5)**

#### **ファイル**: `tests/infrastructure/test_infrastructure_integration.py`

```python
import pytest
import asyncio
from app_2.infrastructure.models.menu_model import MenuModel
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.infrastructure.redis.publisher import RedisPublisher
from app_2.infrastructure.redis.subscriber import RedisSubscriber
from app_2.domain.entities.menu_entity import MenuEntity

@pytest.mark.asyncio
async def test_full_infrastructure_flow():
    """Infrastructure Layer 統合テスト"""
    
    # 1. DB操作テスト
    async with get_db_session() as db:
        repository = MenuRepositoryImpl(db)
        
        # メニュー作成・保存
        menu = MenuEntity(
            id="test-menu-1",
            name="テストメニュー",
            translation="Test Menu",
            category="TEST",
            category_translation="テスト"
        )
        
        saved_menu = await repository.save_with_session(menu, "test-session-1")
        assert saved_menu.id == "test-menu-1"
        
        # セッション取得
        session_menus = await repository.get_by_session_id("test-session-1")
        assert len(session_menus) == 1
        
        # 段階的更新
        updated_menu = await repository.update_translation("test-menu-1", "Updated Test Menu")
        assert updated_menu.translation == "Updated Test Menu"
    
    # 2. Redis Pub/Sub テスト
    publisher = RedisPublisher()
    subscriber = RedisSubscriber()
    
    try:
        # 購読開始
        channel = await publisher.create_sse_channel("test-session-1")
        await subscriber.subscribe(channel)
        
        # メッセージ配信
        test_message = {
            "event": "menu_updated",
            "data": {
                "menu_id": "test-menu-1",
                "translation": "Updated Test Menu"
            }
        }
        
        success = await publisher.publish_json(channel, test_message)
        assert success
        
        # メッセージ受信（タイムアウト付き）
        received = False
        async def receive_message():
            nonlocal received
            async for message in subscriber.listen():
                if message.get("event") == "menu_updated":
                    received = True
                    break
        
        await asyncio.wait_for(receive_message(), timeout=5.0)
        assert received
        
    finally:
        await subscriber.close()
        await publisher.close()
    
    print("✅ Infrastructure Layer 統合テスト完了")

@pytest.mark.asyncio  
async def test_database_performance():
    """データベースパフォーマンステスト"""
    
    async with get_db_session() as db:
        repository = MenuRepositoryImpl(db)
        
        # バッチ保存テスト
        menus = [
            MenuEntity(
                id=f"perf-test-{i}",
                name=f"メニュー{i}",
                translation=f"Menu {i}",
                category="PERFORMANCE",
                category_translation="パフォーマンス"
            )
            for i in range(100)
        ]
        
        import time
        start_time = time.time()
        
        saved_menus = await repository.batch_save_with_session(menus, "perf-session")
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(saved_menus) == 100
        assert duration < 5.0  # 5秒以内での完了を期待
        
        print(f"✅ バッチ保存テスト完了: {duration:.2f}秒で100件保存")

@pytest.mark.asyncio
async def test_error_handling():
    """エラーハンドリングテスト"""
    
    # 無効なデータでのDB操作
    async with get_db_session() as db:
        repository = MenuRepositoryImpl(db)
        
        # 存在しないメニューの更新
        with pytest.raises(Exception):
            await repository.update_translation("non-existent", "test")
        
        # 重複IDでの保存（必要に応じて）
        menu1 = MenuEntity(id="duplicate", name="test1", translation="test1")
        menu2 = MenuEntity(id="duplicate", name="test2", translation="test2")
        
        await repository.save_with_session(menu1, "test-session")
        
        with pytest.raises(Exception):
            await repository.save_with_session(menu2, "test-session")
    
    # Redis接続エラー
    publisher = RedisPublisher()
    # 無効なチャンネルでのテスト等
    
    print("✅ エラーハンドリングテスト完了")
```

---

## ✅ Phase 1 完了チェックリスト

### **Database 拡張**
- [ ] MenuModel に新規フィールド追加完了
- [ ] MenuModel.from_entity_with_session() メソッド実装
- [ ] データベースマイグレーション実行完了
- [ ] フィールド制約・インデックス確認完了

### **Repository 拡張**
- [ ] save_with_session() メソッド実装・テスト完了
- [ ] get_by_session_id() メソッド実装・テスト完了
- [ ] update_* メソッド群実装・テスト完了
- [ ] batch_save_with_session() メソッド実装・テスト完了
- [ ] エラーハンドリング実装・テスト完了

### **Redis Infrastructure**
- [ ] RedisPublisher 実装・テスト完了
- [ ] RedisSubscriber 実装・テスト完了
- [ ] JSON形式メッセージ対応完了
- [ ] 接続管理・エラーハンドリング完了
- [ ] パフォーマンステスト完了

### **Configuration**
- [ ] SSESettings 実装完了
- [ ] ProcessingSettings 実装完了
- [ ] DatabaseSettings 実装完了
- [ ] ファクトリー関数追加完了

### **統合テスト**
- [ ] DB + Redis 統合テスト完了
- [ ] パフォーマンステスト完了
- [ ] エラーハンドリングテスト完了
- [ ] メモリリーク・接続リークテスト完了

---

## 🎯 Phase 1 完了後の状態

### **✅ 完成した機能**
1. **確実なデータ永続化**: セッション管理、段階的更新対応
2. **高速リアルタイム通信**: Redis Pub/Sub による即座配信
3. **堅牢な設定管理**: 環境別設定、パフォーマンスチューニング対応
4. **完全なテスト環境**: 実際のDB・Redisを使用した検証環境

### **🚀 次フェーズへの準備**
- Service Layer は確実な Infrastructure の上で実装可能
- モック不要の統合テスト環境完成
- パフォーマンス要件の事前検証完了

---

## 🔄 Next Steps

Phase 1 完了後、**Phase 2: Service & Domain Layer** に進みます：

1. **Domain Events 定義** - ビジネスイベントの定義
2. **Service Layer 拡張** - 既存サービスの拡張
3. **SSE Events 基本実装** - SSE技術仕様実装

---

**Phase 1 の成功により、後続のフェーズは確実な基盤の上で効率的に開発できます。** 