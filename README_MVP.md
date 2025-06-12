# 🍜 Menu Processor MVP - Production Ready

外国人観光客向けの日本語レストランメニュー翻訳システム（本番環境版）

## 🌟 概要

このMVPは、日本語のレストランメニュー写真を4段階のAI処理で詳細な英語説明付きメニューに変換する実用的なシステムです。Google Search API機能を除外し、本番環境での安定した運用に焦点を当てています。

## 🔧 主な機能

### 4段階処理システム
1. **Stage 1: OCR** - Google Vision APIによる文字認識
2. **Stage 2: カテゴリ分類** - OpenAI Function Callingによる日本語構造化
3. **Stage 3: 翻訳** - OpenAI Function Callingによる英語翻訳
4. **Stage 4: 詳細説明** - 外国人観光客向け詳細説明追加

### 特徴
- ✅ 本番環境に最適化
- ✅ モダンなレスポンシブUI
- ✅ ドラッグ&ドロップ対応
- ✅ リアルタイム進捗表示
- ✅ エラーハンドリング
- ✅ Function Calling による構造化データ
- ✅ 自動ファイルクリーンアップ

## 🚀 セットアップ

### 1. 必要な環境

```bash
Python 3.8+
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env`ファイルを作成し、以下の設定を追加：

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Google Vision API
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
```

### 4. Google Cloud認証の設定

1. Google Cloud Platformでプロジェクトを作成
2. Vision APIを有効化
3. サービスアカウントキーをダウンロード
4. 環境変数にパスを設定

## 📦 起動方法

### 開発環境での起動

```bash
python mvp_menu_processor.py
```

### 本番環境での起動

```bash
uvicorn mvp_menu_processor:app --host 0.0.0.0 --port 8000
```

## 🌐 API仕様

### メインページ
- **URL**: `/`
- **Method**: GET
- **説明**: メインのWebインターフェース

### メニュー処理
- **URL**: `/process-menu`
- **Method**: POST
- **Content-Type**: `multipart/form-data`
- **Parameter**: `file` (画像ファイル)

#### レスポンス例

```json
{
  "stage1": {
    "stage": 1,
    "success": true,
    "extracted_text": "焼き鳥 500円\nてんぷら 800円..."
  },
  "stage2": {
    "stage": 2,
    "success": true,
    "categories": {
      "前菜": [...],
      "メイン": [...],
      "ドリンク": [...],
      "デザート": [...]
    }
  },
  "stage3": {
    "stage": 3,
    "success": true,
    "translated_categories": {
      "Appetizers": [...],
      "Main Dishes": [...],
      "Drinks": [...],
      "Desserts": [...]
    }
  },
  "stage4": {
    "stage": 4,
    "success": true,
    "final_menu": {
      "Appetizers": [
        {
          "japanese_name": "焼き鳥",
          "english_name": "Yakitori",
          "description": "Traditional Japanese grilled chicken skewers, marinated in savory tare sauce and grilled over charcoal for a smoky flavor",
          "price": "500円"
        }
      ]
    }
  }
}
```

### ヘルスチェック
- **URL**: `/health`
- **Method**: GET
- **説明**: システムの稼働状態確認

## 📁 ファイル構成

```
restaurant/
├── mvp_menu_processor.py    # メインアプリケーション
├── requirements.txt         # 依存関係
├── README_MVP.md           # このファイル
├── .env                    # 環境変数（作成が必要）
├── uploads/                # アップロード一時ディレクトリ
└── google-credentials.json # Google Cloud認証（配置が必要）
```

## 🔐 セキュリティ対策

- ✅ アップロードファイルの自動削除
- ✅ ファイル形式の検証
- ✅ 適切なエラーハンドリング
- ✅ 環境変数による機密情報管理

## 🎯 本番環境での考慮事項

### パフォーマンス
- 各段階で個別のエラーハンドリング
- 失敗時の段階的な応答
- 効率的なメモリ使用

### 監視
- ヘルスチェックエンドポイント提供
- 詳細なログ出力
- API利用状況の把握

### スケーラビリティ
- ステートレス設計
- 水平スケーリング対応
- 外部API依存の最小化

## 🛠️ トラブルシューティング

### Google Vision API接続エラー
```
❌ Google Vision API initialization failed
```
**解決方法**: 
1. Google Cloud認証ファイルのパスを確認
2. Vision APIが有効化されているか確認
3. 課金が有効になっているか確認

### OpenAI API設定エラー
```
❌ OpenAI API not configured
```
**解決方法**:
1. `.env`ファイルでOPENAI_API_KEYを設定
2. APIキーの有効性を確認
3. 課金制限を確認

## 📊 使用技術

- **フレームワーク**: FastAPI
- **OCR**: Google Vision API
- **AI処理**: OpenAI GPT-4 with Function Calling
- **フロントエンド**: HTML/CSS/JavaScript (Vanilla)
- **ファイル処理**: aiofiles

## 🔄 更新履歴

### v1.0.0 (MVP版)
- 4段階処理システムの実装
- Google Search API機能の除外
- 本番環境向け最適化
- モダンUI/UXの実装
- エラーハンドリングの強化

## 📞 サポート

技術的な問題や改善要望については、開発チームまでお問い合わせください。

---

**© 2024 Menu Processor MVP - 外国人観光客向けメニュー翻訳システム** 