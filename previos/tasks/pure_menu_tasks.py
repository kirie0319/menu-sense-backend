"""
⚡ Pure Menu Tasks - 純粋なタスク実行層

ビジネスロジックを一切含まず、サービス層からの指示を実行するのみ。
TaskInterface を使用してサービス層に処理を委譲する。
"""

import asyncio
import logging
import time
from typing import Dict, Any

from .celery_app import celery_app
from .utils import redis_client

logger = logging.getLogger(__name__)


def await_sync(coro):
    """非同期関数を同期的に実行（Celeryワーカー用）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_task_interface():
    """TaskInterface インスタンスを取得（エラーハンドリング強化）"""
    try:
        from app.services.dependencies import get_task_interface as get_service_task_interface
        return get_service_task_interface()
    except Exception as e:
        logger.error(f"Failed to get TaskInterface: {e}")
        # フォールバック: 基本的な辞書を返す
        class FallbackTaskInterface:
            def check_task_status(self, session_id: str, item_id: int):
                return type('Response', (), {
                    'success': False,
                    'data': {},
                    'error': f"TaskInterface unavailable: {e}"
                })()
            
            def execute_command(self, command):
                return type('Response', (), {
                    'success': False,
                    'data': {},
                    'error': f"TaskInterface unavailable: {e}"
                })()
        
        return FallbackTaskInterface()


# ===============================================
# 🚀 純粋な実API統合タスク - ビジネスロジックなし
# ===============================================

@celery_app.task(bind=True, queue='real_translate_queue', name="pure_real_translate_menu_item")
def pure_real_translate_menu_item(self, session_id: str, item_id: int, item_text: str, category: str = "Other"):
    """
    純粋な翻訳タスク（ビジネスロジックなし）
    
    サービス層に処理を委譲し、結果をRedisに保存。
    タスク間の依存関係チェックも委譲。
    
    Args:
        session_id: セッションID  
        item_id: アイテムID
        item_text: 日本語テキスト
        category: カテゴリ名
        
    Returns:
        Dict: 処理結果
    """
    
    try:
        logger.info(f"🌍 [PURE_REAL] Starting translation delegation: session={session_id}, item={item_id}")
        
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # 翻訳コマンド作成
        from app.services.menu_processing.task_interface import (
            TaskCommand, CommandType, create_task_command
        )
        from app.services.menu_processing.task_execution_service import TaskStage, ExecutionMode
        
        command = create_task_command(
            command_type=CommandType.EXECUTE_TASK,
            session_id=session_id,
            item_id=item_id,
            stage=TaskStage.TRANSLATION,
            execution_mode=ExecutionMode.REAL,
            payload={
                "item_text": item_text,
                "category": category
            }
        )
        
        # サービス層で実行
        response = await_sync(task_interface.execute_command(command))
        
        if response.success:
            logger.info(f"✅ [PURE_REAL] Translation completed: {session_id}:{item_id}")
            
            # 従来の形式で結果を返す（互換性のため）
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "english_text": response.data.get("translated_text", ""),
                "category": category,
                "provider": "TaskInterface",
                "test_mode": False,
                "execution_time": response.execution_time
            }
        else:
            logger.error(f"❌ [PURE_REAL] Translation failed: {response.error}")
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": response.error
            }
            
    except Exception as e:
        logger.error(f"❌ [PURE_REAL] Task execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e)
        }


@celery_app.task(bind=True, queue='real_description_queue', name="pure_real_generate_menu_description")
def pure_real_generate_menu_description(self, session_id: str, item_id: int, item_text: str, translated_text: str = "", category: str = "Other"):
    """
    純粋な説明生成タスク（ビジネスロジックなし）
    
    サービス層に処理を委譲し、結果をRedisに保存。
    
    Args:
        session_id: セッションID
        item_id: アイテムID
        item_text: 日本語テキスト
        translated_text: 翻訳済みテキスト
        category: カテゴリ名
        
    Returns:
        Dict: 処理結果
    """
    
    try:
        logger.info(f"📝 [PURE_REAL] Starting description delegation: session={session_id}, item={item_id}")
        
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # 説明生成コマンド作成
        from app.services.menu_processing.task_interface import (
            TaskCommand, CommandType, create_task_command
        )
        from app.services.menu_processing.task_execution_service import TaskStage, ExecutionMode
        
        command = create_task_command(
            command_type=CommandType.EXECUTE_TASK,
            session_id=session_id,
            item_id=item_id,
            stage=TaskStage.DESCRIPTION,
            execution_mode=ExecutionMode.REAL,
            payload={
                "item_text": item_text,
                "category": category
            },
            metadata={
                "translated_text": translated_text
            }
        )
        
        # サービス層で実行
        response = await_sync(task_interface.execute_command(command))
        
        if response.success:
            logger.info(f"✅ [PURE_REAL] Description completed: {session_id}:{item_id}")
            
            # 従来の形式で結果を返す（互換性のため）
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "description": response.data.get("description", ""),
                "ingredients": response.data.get("ingredients", []),
                "preparation": response.data.get("preparation", ""),
                "category": category,
                "provider": "TaskInterface",
                "test_mode": False,
                "execution_time": response.execution_time
            }
        else:
            logger.error(f"❌ [PURE_REAL] Description failed: {response.error}")
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": response.error
            }
            
    except Exception as e:
        logger.error(f"❌ [PURE_REAL] Task execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e)
        }


@celery_app.task(bind=True, queue='real_image_queue', name="pure_real_generate_menu_image")
def pure_real_generate_menu_image(self, session_id: str, item_id: int, item_text: str, description: str = "", category: str = "Other"):
    """
    純粋な画像生成タスク（ビジネスロジックなし）
    
    サービス層に処理を委譲し、結果をRedisに保存。
    
    Args:
        session_id: セッションID
        item_id: アイテムID
        item_text: 日本語テキスト
        description: 詳細説明
        category: カテゴリ名
        
    Returns:
        Dict: 処理結果
    """
    
    try:
        logger.info(f"🖼️ [PURE_REAL] Starting image delegation: session={session_id}, item={item_id}")
        
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # 画像生成コマンド作成
        from app.services.menu_processing.task_interface import (
            TaskCommand, CommandType, create_task_command
        )
        from app.services.menu_processing.task_execution_service import TaskStage, ExecutionMode
        
        command = create_task_command(
            command_type=CommandType.EXECUTE_TASK,
            session_id=session_id,
            item_id=item_id,
            stage=TaskStage.IMAGE,
            execution_mode=ExecutionMode.REAL,
            payload={
                "item_text": item_text,
                "category": category
            },
            metadata={
                "description": description
            }
        )
        
        # サービス層で実行
        response = await_sync(task_interface.execute_command(command))
        
        if response.success:
            logger.info(f"✅ [PURE_REAL] Image generation completed: {session_id}:{item_id}")
            
            # 従来の形式で結果を返す（互換性のため）
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "image_url": response.data.get("image_url", ""),
                "image_path": response.data.get("image_path", ""),
                "prompt_used": response.data.get("prompt_used", ""),
                "category": category,
                "provider": "TaskInterface",
                "test_mode": False,
                "execution_time": response.execution_time
            }
        else:
            logger.error(f"❌ [PURE_REAL] Image generation failed: {response.error}")
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": response.error
            }
            
    except Exception as e:
        logger.error(f"❌ [PURE_REAL] Task execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e)
        }


# ===============================================
# 🧪 純粋なテストタスク - ビジネスロジックなし
# ===============================================

@celery_app.task(bind=True, queue='translate_queue', name="pure_test_translate_menu_item")
def pure_test_translate_menu_item(self, session_id: str, item_id: int, item_text: str):
    """
    純粋なテスト翻訳タスク（ビジネスロジックなし）
    
    Args:
        session_id: セッションID  
        item_id: アイテムID
        item_text: 日本語テキスト
        
    Returns:
        Dict: 処理結果
    """
    
    try:
        logger.info(f"🧪 [PURE_TEST] Starting test translation delegation: session={session_id}, item={item_id}")
        
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # テスト翻訳コマンド作成
        from app.services.menu_processing.task_interface import (
            TaskCommand, CommandType, create_task_command
        )
        from app.services.menu_processing.task_execution_service import TaskStage, ExecutionMode
        
        command = create_task_command(
            command_type=CommandType.EXECUTE_TASK,
            session_id=session_id,
            item_id=item_id,
            stage=TaskStage.TRANSLATION,
            execution_mode=ExecutionMode.TEST,
            payload={
                "item_text": item_text,
                "category": "Test"
            }
        )
        
        # サービス層で実行
        response = await_sync(task_interface.execute_command(command))
        
        if response.success:
            logger.info(f"✅ [PURE_TEST] Test translation completed: {session_id}:{item_id}")
            
            # 従来の形式で結果を返す（互換性のため）
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "english_text": response.data.get("translated_text", ""),
                "provider": "TaskInterface_Test",
                "test_mode": True,
                "execution_time": response.execution_time
            }
        else:
            logger.error(f"❌ [PURE_TEST] Test translation failed: {response.error}")
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": response.error
            }
            
    except Exception as e:
        logger.error(f"❌ [PURE_TEST] Task execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e)
        }


@celery_app.task(bind=True, queue='description_queue', name="pure_test_generate_menu_description")
def pure_test_generate_menu_description(self, session_id: str, item_id: int, item_text: str):
    """
    純粋なテスト説明生成タスク（ビジネスロジックなし）
    
    Args:
        session_id: セッションID
        item_id: アイテムID
        item_text: 日本語テキスト
        
    Returns:
        Dict: 処理結果
    """
    
    try:
        logger.info(f"🧪 [PURE_TEST] Starting test description delegation: session={session_id}, item={item_id}")
        
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # テスト説明生成コマンド作成
        from app.services.menu_processing.task_interface import (
            TaskCommand, CommandType, create_task_command
        )
        from app.services.menu_processing.task_execution_service import TaskStage, ExecutionMode
        
        command = create_task_command(
            command_type=CommandType.EXECUTE_TASK,
            session_id=session_id,
            item_id=item_id,
            stage=TaskStage.DESCRIPTION,
            execution_mode=ExecutionMode.TEST,
            payload={
                "item_text": item_text,
                "category": "Test"
            }
        )
        
        # サービス層で実行
        response = await_sync(task_interface.execute_command(command))
        
        if response.success:
            logger.info(f"✅ [PURE_TEST] Test description completed: {session_id}:{item_id}")
            
            # 従来の形式で結果を返す（互換性のため）
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "description": response.data.get("description", ""),
                "ingredients": response.data.get("ingredients", []),
                "preparation": response.data.get("preparation", ""),
                "provider": "TaskInterface_Test",
                "test_mode": True,
                "execution_time": response.execution_time
            }
        else:
            logger.error(f"❌ [PURE_TEST] Test description failed: {response.error}")
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": response.error
            }
            
    except Exception as e:
        logger.error(f"❌ [PURE_TEST] Task execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e)
        }


# ===============================================
# 📊 純粋な状態管理関数 - ビジネスロジックなし
# ===============================================

def pure_get_real_status(session_id: str, item_id: int = None) -> Dict[str, Any]:
    """
    純粋な状態取得関数（ビジネスロジックなし）
    
    TaskInterface を使用してサービス層に委譲。
    
    Args:
        session_id: セッションID
        item_id: アイテムID（オプション）
        
    Returns:
        Dict: 状態情報
    """
    
    try:
        # TaskInterface を使用してサービス層に委譲
        task_interface = get_task_interface()
        
        # FallbackTaskInterfaceの場合は早期リターン
        if hasattr(task_interface, '__class__') and task_interface.__class__.__name__ == 'FallbackTaskInterface':
            return {
                "error": "TaskInterface unavailable",
                "session_id": session_id,
                "item_id": item_id,
                "success": False,
                "fallback": True
            }
        
        if item_id is not None:
            # 特定アイテムの状態取得
            response = await_sync(task_interface.check_task_status(session_id, item_id))
            if hasattr(response, 'success') and response.success:
                return response.data if isinstance(response.data, dict) else {"data": response.data}
            else:
                return {"error": getattr(response, 'error', 'Unknown error'), "success": False}
        else:
            # セッション全体の進捗取得
            from app.services.menu_processing.task_interface import (
                TaskCommand, CommandType, create_task_command
            )
            from app.services.menu_processing.task_execution_service import TaskStage
            
            command = create_task_command(
                command_type=CommandType.GET_PROGRESS,
                session_id=session_id,
                item_id=0,  # ダミー
                stage=TaskStage.TRANSLATION  # ダミー
            )
            
            response = await_sync(task_interface.execute_command(command))
            if hasattr(response, 'success') and response.success:
                return response.data if isinstance(response.data, dict) else {"data": response.data}
            else:
                return {"error": getattr(response, 'error', 'Unknown error'), "success": False}
                
    except Exception as e:
        # エラー時は辞書形式で返す
        return {
            "error": str(e),
            "session_id": session_id,
            "item_id": item_id,
            "success": False,
            "exception": True
        }


# pure_test_redis_connection関数は削除されました
# Redis接続チェックは簡略化されました


# ===============================================
# Export
# ===============================================

__all__ = [
    # Pure real tasks
    "pure_real_translate_menu_item",
    "pure_real_generate_menu_description", 
    "pure_real_generate_menu_image",
    
    # Pure test tasks
    "pure_test_translate_menu_item",
    "pure_test_generate_menu_description",
    
    # Pure utility functions
    "pure_get_real_status"
]