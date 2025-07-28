# 🚀 app_2 実装計画書

## 📋 プロジェクト概要

**AI メニュー翻訳・解析システム v2.0**の実装計画書  
Clean Architecture + YAML管理システム基盤完成後の次期実装フェーズ

---

## ✅ 完成済み基盤コンポーネント

| コンポーネント | 状況 | 詳細 |
|---------------|------|------|
| **PromptLoader** | ✅ 完全実装 | YAML管理、テンプレート変数置換、エラーハンドリング |
| **OpenAI統合** | ✅ 完全実装 | 4クライアント（description/allergen/ingredient/categorize） |
| **Google API統合** | ✅ 完全実装 | Vision/Translate/Search + 一元認証管理 |
| **設定システム** | ✅ 完全実装 | 環境変数管理、バリデーション、設定サマリー |
| **データベース** | ✅ 完全実装 | 非同期接続、自動初期化、MenuModel |
| **ドメインエンティティ** | ✅ 完全実装 | MenuEntity、ビジネスロジック |
| **インフラ基盤** | ✅ 完全実装 | AWS S3、Secrets Manager |
| **テストスイート** | ✅ 完全実装 | 包括的テストカバレッジ（45+ テスト） |

---

## 🎯 実装順序と技術的根拠

### 📊 依存関係図

```
┌─────────────────┐
│   API Layer     │ ← FastAPI エンドポイント
│  (endpoints/)   │
└─────────────────┘
         ↓ 依存
┌─────────────────┐
│ Pipeline Layer  │ ← フロー制御・オーケストレーション
│  (pipelines/)   │
└─────────────────┘
         ↓ 依存
┌─────────────────┐
│  Task Layer     │ ← Celery 非同期タスク
│   (tasks/)      │
└─────────────────┘
         ↓ 依存
┌─────────────────┐
│ Service Layer   │ ← ビジネスロジック（🎯 開始点）
│  (services/)    │
└─────────────────┘
         ↓ 依存
┌─────────────────┐
│Infrastructure   │ ← 外部API統合（✅ 完成済み）
│ (integrations/) │
└─────────────────┘
```

### 🔄 実装順序の理由

| 順序 | レイヤー | 理由 | メリット |
|------|---------|------|---------|
| **1st** | **Services層** | 最下位依存・Pure Logic | 単体テスト容易・段階的確認 |
| **2nd** | **Tasks層** | Services利用・非同期処理 | 並列処理検証・Celery動作確認 |
| **3rd** | **Pipelines層** | Tasks制御・複雑フロー | オーケストレーション・SSE準備 |
| **4th** | **API層** | 全層統合・ユーザー向け | E2Eテスト・完全動作確認 |

---

## 🚀 フェーズ1：Services層実装

### 📝 実装対象ファイル

```
app_2/services/
├── ocr_service.py           # 🎯 開始点（OCR処理）
├── translate_service.py     # 翻訳サービス
├── categorize_service.py    # カテゴライズサービス
├── describe_service.py      # 詳細説明生成
├── allergen_service.py      # アレルゲン抽出
├── ingredient_service.py    # 含有物抽出
├── search_image_service.py  # Google画像検索
└── image_service.py        # 画像処理統合
```

### 🎯 実装開始：OCR Service

**なぜOCRから？**
- 処理フローの起点
- 外部依存が最小（GoogleVisionClientのみ）
- 他のサービスの前提条件

```python
# app_2/services/ocr_service.py 実装例
"""
OCR Service - Menu Processor v2
Google Vision API を使用したテキスト抽出サービス
"""
from typing import List
from app_2.infrastructure.integrations.google import GoogleVisionClient
from app_2.utils.logger import get_logger

logger = get_logger("ocr_service")

class OCRService:
    """OCR処理サービス"""
    
    def __init__(self):
        self.vision_client = GoogleVisionClient()
    
    async def extract_text_from_image(self, image_data: bytes) -> List[str]:
        """
        画像からテキストを抽出
        
        Args:
            image_data: 画像バイナリデータ
            
        Returns:
            List[str]: 抽出されたテキスト行
        """
        try:
            texts = await self.vision_client.extract_text(image_data)
            logger.info(f"OCR completed: {len(texts)} text blocks extracted")
            return texts
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise
    
    def extract_menu_items(self, texts: List[str]) -> List[str]:
        """
        テキストからメニュー項目を抽出（フィルタリング）
        
        Args:
            texts: OCR抽出テキスト
            
        Returns:
            List[str]: メニュー項目リスト
        """
        # 基本的なフィルタリングロジック
        menu_items = []
        for text in texts:
            if self._is_likely_menu_item(text):
                menu_items.append(text.strip())
        
        return menu_items
    
    def _is_likely_menu_item(self, text: str) -> bool:
        """メニュー項目らしさの判定"""
        if len(text.strip()) < 2:
            return False
        # 価格らしい文字列を除外
        if any(char in text for char in ['¥', '$', '円', '価格']):
            return False
        return True
```

### ✅ OCR Service チェックポイント

- [ ] GoogleVisionClient連携動作
- [ ] テキスト抽出機能
- [ ] メニュー項目フィルタリング
- [ ] エラーハンドリング
- [ ] ログ出力
- [ ] 単体テスト作成

### 🔄 Services層実装順序

1. **OCR Service** → 2. **Translate Service** → 3. **Categorize Service**
4. **Describe Service** → 5. **Allergen Service** → 6. **Ingredient Service**
7. **Search Image Service** → 8. **Image Service（統合）**

### 📋 各サービス実装仕様

| サービス | 主要機能 | 依存コンポーネント | 期待入力/出力 |
|---------|---------|------------------|-------------|
| **OCRService** | 画像→テキスト抽出 | GoogleVisionClient | bytes → List[str] |
| **TranslateService** | テキスト翻訳 | GoogleTranslateClient | str → str |
| **CategorizeService** | メニューカテゴライズ | OpenAI CategorizeClient | str → str |
| **DescribeService** | 詳細説明生成 | OpenAI DescriptionClient | str → str |
| **AllergenService** | アレルゲン抽出 | OpenAI AllergenClient | str → str |
| **IngredientService** | 含有物抽出 | OpenAI IngredientClient | str → str |
| **SearchImageService** | 画像検索 | GoogleSearchClient | str → List[Dict] |
| **ImageService** | 画像処理統合 | AWS S3 + 画像生成API | Dict → str |

---

## 🚀 フェーズ2：Tasks層実装

### 📝 実装対象ファイル

```
app_2/tasks/
├── translate_task.py        # 翻訳タスク
├── describe_task.py         # 詳細説明タスク
├── allergen_task.py         # アレルゲン抽出タスク
├── ingredient_task.py       # 含有物抽出タスク
└── search_image_task.py     # 画像検索タスク
```

### 🎯 Celery統合パターン

```python
# app_2/tasks/translate_task.py 実装例
"""
Translate Task - Menu Processor v2
非同期翻訳処理タスク
"""
from app_2.core.celery_app import celery_app
from app_2.services.translate_service import TranslateService
from app_2.utils.logger import get_logger

logger = get_logger("translate_task")

@celery_app.task(queue='translation_queue', bind=True)
async def translate_menu_item(self, menu_item: str, target_language: str = "ja") -> str:
    """
    メニュー項目翻訳タスク
    
    Args:
        menu_item: 翻訳対象テキスト
        target_language: 目標言語（デフォルト：日本語）
        
    Returns:
        str: 翻訳結果
    """
    try:
        service = TranslateService()
        translated = await service.translate(menu_item, target_language)
        
        logger.info(f"Translation completed: {menu_item} → {translated}")
        return translated
        
    except Exception as e:
        logger.error(f"Translation task failed: {e}")
        self.retry(countdown=60, max_retries=3)
```

### ✅ Tasks層チェックポイント

- [ ] Celery統合動作
- [ ] キュー分離設定
- [ ] リトライ機構
- [ ] エラーハンドリング
- [ ] 非同期処理確認
- [ ] Services層呼び出し確認

---

## 🚀 フェーズ3：Pipelines層実装

### 📝 実装対象ファイル

```
app_2/pipelines/
├── pipeline_runner.py       # パイプライン実行制御
├── pipeline_def.py          # パイプライン定義
└── context_store.py         # 実行コンテキスト管理
```

### 🎯 パイプライン実行フロー

```python
# app_2/pipelines/pipeline_runner.py 実装例
"""
Pipeline Runner - Menu Processor v2
メニュー処理パイプラインの実行制御
"""
from typing import List, Dict, Any
from app_2.tasks import (
    translate_task, describe_task, allergen_task, 
    ingredient_task, search_image_task
)
from app_2.services.ocr_service import OCRService
from app_2.services.categorize_service import CategorizeService
from app_2.pipelines.context_store import ContextStore
from app_2.utils.logger import get_logger

logger = get_logger("pipeline_runner")

class PipelineRunner:
    """メニュー処理パイプライン実行制御"""
    
    def __init__(self):
        self.ocr_service = OCRService()
        self.categorize_service = CategorizeService()
        self.context_store = ContextStore()
    
    async def run_menu_processing_pipeline(
        self, 
        menu_id: str, 
        image_data: bytes
    ) -> Dict[str, Any]:
        """
        メニュー処理パイプライン実行
        
        フロー：OCR → カテゴライズ → 5並列タスク実行
        
        Args:
            menu_id: メニューID
            image_data: 画像データ
            
        Returns:
            Dict: 処理結果コンテキスト
        """
        context = self.context_store.create_context(menu_id)
        
        try:
            # フェーズ1: OCR処理
            logger.info(f"Phase 1: OCR processing for {menu_id}")
            texts = await self.ocr_service.extract_text_from_image(image_data)
            menu_items = self.ocr_service.extract_menu_items(texts)
            
            if not menu_items:
                raise ValueError("No menu items detected")
            
            primary_item = menu_items[0]  # 最初の項目をメイン処理対象
            context.update_ocr_result(primary_item, menu_items)
            
            # フェーズ2: カテゴライズ
            logger.info(f"Phase 2: Categorizing {primary_item}")
            category = await self.categorize_service.categorize(primary_item)
            context.update_category(category)
            
            # フェーズ3: 5並列タスク起動
            logger.info(f"Phase 3: Starting 5 parallel tasks for {primary_item}")
            task_results = await self._execute_parallel_tasks(primary_item)
            context.update_task_results(task_results)
            
            logger.info(f"Pipeline completed for {menu_id}")
            return context.get_final_result()
            
        except Exception as e:
            logger.error(f"Pipeline failed for {menu_id}: {e}")
            context.mark_failed(str(e))
            raise
    
    async def _execute_parallel_tasks(self, menu_item: str) -> Dict[str, Any]:
        """5つのタスクを並列実行"""
        import asyncio
        
        # 並列タスク起動
        tasks = {
            'translation': translate_task.delay(menu_item),
            'description': describe_task.delay(menu_item),
            'allergen': allergen_task.delay(menu_item),
            'ingredient': ingredient_task.delay(menu_item),
            'search': search_image_task.delay(menu_item)
        }
        
        # 結果収集
        results = {}
        for task_name, task in tasks.items():
            try:
                results[task_name] = await task
                logger.info(f"Task {task_name} completed")
            except Exception as e:
                logger.error(f"Task {task_name} failed: {e}")
                results[task_name] = None
        
        return results
```

### ✅ Pipelines層チェックポイント

- [ ] OCR → カテゴライズフロー
- [ ] 5並列タスク実行
- [ ] コンテキスト管理
- [ ] エラーハンドリング
- [ ] ログ追跡
- [ ] SSE準備（イベント配信）

---

## 🚀 フェーズ4：API層実装

### 📝 実装対象ファイル

```
app_2/api/v1/endpoints/
├── pipeline.py              # メイン処理エンドポイント
├── sse.py                   # SSE通信エンドポイント
└── image_generate.py        # 画像生成エンドポイント
```

### 🎯 メインAPIエンドポイント

```python
# app_2/api/v1/endpoints/pipeline.py 実装例
"""
Pipeline API - Menu Processor v2
メニュー処理パイプラインのAPIエンドポイント
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
from app_2.pipelines.pipeline_runner import PipelineRunner
from app_2.domain.repositories.menu_repository import MenuRepositoryInterface
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.utils.id_gen import generate_menu_id
from app_2.utils.logger import get_logger

logger = get_logger("pipeline_api")
router = APIRouter()

@router.post("/process", response_model=Dict[str, Any])
async def process_menu_image(
    image: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    メニュー画像処理開始
    
    フロー：画像アップロード → OCR → カテゴライズ → 5並列処理
    
    Args:
        image: アップロードされた画像ファイル
        
    Returns:
        Dict: 処理開始結果
    """
    try:
        # バリデーション
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # 画像データ読み込み
        image_data = await image.read()
        menu_id = generate_menu_id()
        
        logger.info(f"Processing started for menu {menu_id}")
        
        # パイプライン実行
        pipeline_runner = PipelineRunner()
        result = await pipeline_runner.run_menu_processing_pipeline(
            menu_id, image_data
        )
        
        # データベース保存
        menu_repo: MenuRepositoryInterface = MenuRepositoryImpl()
        await menu_repo.save(result['menu_entity'])
        
        return {
            "menu_id": menu_id,
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Menu processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{menu_id}")
async def get_processing_status(menu_id: str) -> Dict[str, Any]:
    """処理状況確認"""
    # 実装予定
    pass
```

### ✅ API層チェックポイント

- [ ] FastAPI統合
- [ ] ファイルアップロード処理
- [ ] パイプライン呼び出し
- [ ] データベース保存
- [ ] エラーハンドリング
- [ ] レスポンス形式
- [ ] SSE統合

---

## 🧪 各フェーズのテスト戦略

### 📋 テスト実行計画

| フェーズ | テスト種別 | コマンド例 | 検証内容 |
|---------|-----------|-----------|---------|
| **Services** | 単体テスト | `pytest tests/services/ -v` | ビジネスロジック |
| **Tasks** | 統合テスト | `pytest tests/tasks/ -v` | Celery連携 |
| **Pipelines** | フローテスト | `pytest tests/pipelines/ -v` | 処理フロー |
| **API** | E2Eテスト | `pytest tests/api/ -v` | 全体動作 |

### 🔧 テスト用データ準備

```bash
# テスト画像準備
cp test_image.webp app_2/tests/fixtures/

# 環境変数設定
export TESTING=true
export OPENAI_API_KEY="test-key"
export GOOGLE_CLOUD_PROJECT_ID="test-project"
```

---

## 📈 実装進捗管理

### ✅ チェックリスト

#### フェーズ1: Services層
- [ ] OCRService実装
- [ ] TranslateService実装
- [ ] CategorizeService実装
- [ ] DescribeService実装
- [ ] AllergenService実装
- [ ] IngredientService実装
- [ ] SearchImageService実装
- [ ] ImageService実装
- [ ] Services層単体テスト

#### フェーズ2: Tasks層
- [ ] translate_task実装
- [ ] describe_task実装
- [ ] allergen_task実装
- [ ] ingredient_task実装
- [ ] search_image_task実装
- [ ] Tasks層統合テスト

#### フェーズ3: Pipelines層
- [ ] PipelineRunner実装
- [ ] PipelineDef実装
- [ ] ContextStore実装
- [ ] SSE統合準備
- [ ] Pipelines層フローテスト

#### フェーズ4: API層
- [ ] pipeline.py実装
- [ ] sse.py実装
- [ ] image_generate.py実装
- [ ] ルーター統合
- [ ] API層E2Eテスト

#### 統合フェーズ
- [ ] 全体統合テスト
- [ ] パフォーマンステスト
- [ ] エラーシナリオテスト
- [ ] ドキュメント更新

---

## 🎯 実装時の注意点

### ⚠️ 共通注意事項

1. **ログ出力の一貫性**：全サービスで統一されたログ形式使用
2. **エラーハンドリング**：適切な例外型とメッセージ設定
3. **設定管理**：`settings`オブジェクトからの設定読み込み
4. **テスト可能性**：依存性注入とモック対応
5. **型ヒント**：すべての関数・メソッドに型注釈

### 🔧 開発環境セットアップ

```bash
# 依存関係インストール
pip install -r requirements.txt

# Redis起動（Celery用）
redis-server

# Celeryワーカー起動
celery -A app_2.core.celery_app worker --loglevel=info

# 開発サーバー起動
cd app_2 && python main.py
```

---

## 🏁 完成後の期待動作

### 🎯 ユーザーフロー

1. **画像アップロード** → POST `/process`
2. **リアルタイム更新** → SSE接続でタスク進捗受信
3. **結果確認** → GET `/status/{menu_id}`
4. **画像生成要求** → POST `/generate-image` (オプション)

### 📊 システム性能目標

- **OCR処理時間**：3秒以内
- **並列タスク完了**：10秒以内
- **API レスポンス**：500ms以内
- **同時処理数**：50リクエスト/分

---

この実装計画に従って、確実で効率的な開発を進めましょう！🚀 