# 📚 Menu Sensor Backend API リファレンス

## 🔄 最新更新（2025年1月2日）

**リファクタリング完了**: Enhanced機能統合により、全APIに品質指標・統計機能が追加されました。

## 🌟 Enhanced機能対応サービス

### Translation Service
- **品質指標**: `quality_score`, `confidence`, `translation_coverage`
- **統計**: 成功率、平均処理時間、エラー率
- **メタデータ**: 処理詳細情報

### Category Service  
- **品質指標**: `coverage_score`, `balance_score`, `accuracy_estimate`
- **カテゴリ分析**: バランス評価、カバレッジ分析
- **日本語検出**: Unicode対応正規表現

### OCR Service
- **品質指標**: `text_clarity_score`, `character_count`, `japanese_character_ratio`
- **テキスト分析**: 文字数、言語比率、明瞭度
- **処理統計**: 成功率、平均処理時間

### Description Service
- **品質指標**: `cultural_accuracy`, `description_coverage`, `description_quality`
- **文化的評価**: 文化的正確性、説明品質
- **フォールバック**: 自動フォールバック管理

### Image Service
- **品質指標**: `visual_quality`, `prompt_effectiveness`, `generation_success_rate`
- **視覚評価**: 画像品質、プロンプト効果
- **ストレージ統計**: タイプ別統計、S3統合

## 📊 新しいレスポンス形式

### 標準レスポンス構造
```python
{
    # 従来のレスポンス内容（完全互換）
    "result": "translated_text",
    "original_text": "元のテキスト",
    
    # 新しいEnhanced機能
    "quality_score": 0.95,           # 品質スコア (0.0-1.0)
    "confidence": 0.92,              # 信頼度 (0.0-1.0)
    "processing_metadata": {         # 処理メタデータ
        "processing_time": 1.23,
        "service_version": "enhanced",
        "model_used": "gpt-4"
    }
}
```

### Translation API レスポンス例
```json
{
    "translated_text": "Delicious sushi",
    "original_text": "美味しい寿司",
    "quality_score": 0.95,
    "confidence": 0.92,
    "translation_coverage": 1.0,
    "consistency_score": 0.88,
    "processing_metadata": {
        "processing_time": 1.45,
        "service_version": "enhanced_v1.0",
        "model_used": "gpt-4",
        "language_detected": "japanese"
    }
}
```

### OCR API レスポンス例
```json
{
    "extracted_text": "天ぷら定食 ¥1200",
    "confidence": 0.94,
    "text_clarity_score": 0.89,
    "character_count": 8,
    "japanese_character_ratio": 0.75,
    "processing_metadata": {
        "processing_time": 2.1,
        "service_version": "enhanced_v1.0",
        "vision_api_version": "v1",
        "image_quality": "high"
    }
}
```

## 🛠️ サービス統計API

### 統計情報取得
各サービスで統計情報を取得可能：

```python
# Translation Service統計
GET /api/v1/translation/statistics

{
    "total_requests": 1250,
    "success_rate": 0.96,
    "average_processing_time": 1.34,
    "average_quality_score": 0.91,
    "error_rate": 0.04,
    "last_24h_requests": 89
}
```

## 📋 API エンドポイント一覧

### Core Endpoints
- `GET /` - メイン画面
- `GET /health` - ヘルスチェック
- `GET /diagnostic` - システム診断

### Translation APIs
- `POST /api/v1/translate/text` - テキスト翻訳
- `POST /api/v1/translate/batch` - バッチ翻訳
- `GET /api/v1/translate/statistics` - 翻訳統計

### OCR APIs  
- `POST /api/v1/ocr/extract` - テキスト抽出
- `POST /api/v1/ocr/analyze` - 画像分析
- `GET /api/v1/ocr/statistics` - OCR統計

### Category APIs
- `POST /api/v1/category/classify` - カテゴリ分類
- `POST /api/v1/category/analyze` - カテゴリ分析
- `GET /api/v1/category/statistics` - カテゴリ統計

### Description APIs
- `POST /api/v1/description/generate` - 説明生成
- `POST /api/v1/description/enhance` - 説明強化
- `GET /api/v1/description/statistics` - 説明統計

### Image APIs
- `POST /api/v1/image/generate` - 画像生成
- `POST /api/v1/image/batch` - バッチ画像生成
- `GET /api/v1/image/statistics` - 画像統計

### Menu Parallel APIs（分割済み）
- `POST /api/v1/menu-parallel/process` - メニュー並列処理
- `GET /api/v1/menu-parallel/stream/{session_id}` - SSEストリーミング
- `GET /api/v1/menu-parallel/status/{session_id}` - 処理状態確認
- `GET /api/v1/menu-parallel/statistics` - 並列処理統計

## 🔧 使用例

### Python SDK使用例
```python
from app.services.translation.base import BaseTranslationService
from app.services.ocr.base import BaseOCRService

# Translation with enhanced features
translation_service = BaseTranslationService()
result = await translation_service.translate_text(
    text="美味しい寿司",
    target_language="english"
)

print(f"翻訳結果: {result.translated_text}")
print(f"品質スコア: {result.quality_score}")
print(f"信頼度: {result.confidence}")

# OCR with enhanced features  
ocr_service = BaseOCRService()
ocr_result = await ocr_service.extract_text(image_data)

print(f"抽出テキスト: {ocr_result.extracted_text}")
print(f"明瞭度: {ocr_result.text_clarity_score}")
print(f"文字数: {ocr_result.character_count}")

# Statistics retrieval
stats = translation_service.get_statistics()
print(f"成功率: {stats['success_rate']}")
print(f"平均処理時間: {stats['average_processing_time']}秒")
```

### HTTP API使用例
```bash
# Enhanced Translation
curl -X POST "http://localhost:8000/api/v1/translate/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "美味しい寿司", "target_language": "english"}'

# Enhanced OCR
curl -X POST "http://localhost:8000/api/v1/ocr/extract" \
  -F "file=@menu_image.jpg"

# Statistics
curl "http://localhost:8000/api/v1/translation/statistics"
```

## 🔒 認証・セキュリティ

### 統一認証システム
- **AWS Secrets Manager**: 本番環境推奨
- **環境変数**: 開発環境用
- **IAM Role**: ECS/EC2環境用

### API キー管理
```bash
# 必要なAPI キー
OPENAI_API_KEY=your_openai_key
GOOGLE_CREDENTIALS_JSON=your_google_credentials
GEMINI_API_KEY=your_gemini_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

## 📈 監視・ログ

### ヘルスチェック
```bash
curl http://localhost:8000/health

{
    "status": "healthy",
    "services": {
        "translation": true,
        "ocr": true,
        "category": true,
        "description": true,
        "image": true
    },
    "enhanced_features": true,
    "version": "refactored_v1.0"
}
```

### システム診断
```bash
curl http://localhost:8000/diagnostic

{
    "system_status": "optimal",
    "service_statistics": {
        "translation": {"success_rate": 0.96, "avg_time": 1.34},
        "ocr": {"success_rate": 0.94, "avg_time": 2.1},
        "category": {"success_rate": 0.92, "avg_time": 0.8}
    },
    "performance_metrics": {
        "cpu_usage": "45%",
        "memory_usage": "67%",
        "disk_usage": "23%"
    }
}
```

## 🚨 エラーハンドリング

### 標準エラーレスポンス
```json
{
    "error": true,
    "error_code": "TRANSLATION_FAILED",
    "message": "Translation service temporarily unavailable",
    "details": {
        "service": "translation",
        "retry_after": 30,
        "fallback_available": true
    },
    "timestamp": "2025-01-02T10:30:00Z"
}
```

### 一般的なエラーコード
- `SERVICE_UNAVAILABLE`: サービス利用不可
- `INVALID_INPUT`: 無効な入力データ
- `QUOTA_EXCEEDED`: APIクォータ超過
- `AUTHENTICATION_FAILED`: 認証失敗
- `PROCESSING_TIMEOUT`: 処理タイムアウト

## 📞 サポート

### トラブルシューティング
1. **ヘルスチェック**: `GET /health`で状態確認
2. **診断**: `GET /diagnostic`で詳細診断
3. **統計確認**: 各サービスの統計エンドポイント
4. **ログ確認**: アプリケーションログの確認

### 緊急時の対応
- バックアップファイルからの復旧
- フォールバック機能の活用
- 段階的なサービス復旧

---

## 📋 更新履歴

- **v1.0** (2025-01-02): Enhanced機能統合、リファクタリング完了
- **v0.9** (2024-12): 画像生成機能改善
- **v0.8** (2024-11): S3ストレージ統合

**📚 Menu Sensor Backend API - Enhanced Edition** 