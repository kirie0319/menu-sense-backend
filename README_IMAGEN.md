# Imagen 3 (Gemini API) テストガイド

このプロジェクトでImagen 3（Gemini API経由）の画像生成機能をテストするためのガイドです。

## 🚀 セットアップ手順

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com)にアクセス
2. 「Get API key」をクリック
3. 新しいAPIキーを作成
4. **重要**: Imagen 3は有料ティア（Paid Tier）でのみ利用可能

### 3. 環境変数の設定

`.env`ファイルを作成し、以下の設定を追加：

```bash
# Imagen 3 (Gemini API)
GEMINI_API_KEY=your_gemini_api_key_here

# 既存の設定も必要（他の機能用）
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

## 🧪 テストの実行

### 基本テスト

```bash
python test_imagen.py
```

このテストでは以下をチェックします：
- GEMINI_API_KEYの設定確認
- google-genaiライブラリのインポート
- Gemini クライアントの初期化
- 画像生成機能（3種類のテスト画像）
- 複数画像一括生成（4枚）
- 異なるアスペクト比での生成

### テスト結果

成功した場合、以下の画像が`uploads/`ディレクトリに生成されます：
- `imagen_test_1_[timestamp].png` - 日本のお弁当
- `imagen_test_2_[timestamp].png` - モダンなレストランメニュー
- `imagen_test_3_[timestamp].png` - 新鮮な寿司プレート
- `imagen_batch_1-4_[timestamp].png` - 一括生成画像
- `imagen_ratio_[ratio]_[timestamp].png` - 異なるアスペクト比の画像

## 🎨 主な機能

### 1. テキストから画像生成

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# クライアント初期化
client = genai.Client(api_key='your_api_key')

# 画像生成
response = client.models.generate_images(
    model='imagen-3.0-generate-002',
    prompt='A delicious Japanese bento box',
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1"
    )
)

# 画像保存
for generated_image in response.generated_images:
    image = Image.open(BytesIO(generated_image.image.image_bytes))
    image.save("generated_image.png")
```

### 2. 複数画像の一括生成

```python
# 最大4枚まで一度に生成可能
response = client.models.generate_images(
    model='imagen-3.0-generate-002',
    prompt='Cute food mascot characters',
    config=types.GenerateImagesConfig(
        number_of_images=4,  # 1-4の範囲
        aspect_ratio="1:1"
    )
)
```

## 📋 パラメータオプション

### aspect_ratio（アスペクト比）
- `"1:1"` - 正方形（デフォルト）
- `"3:4"` - 縦長
- `"4:3"` - 横長
- `"9:16"` - スマートフォン縦画面
- `"16:9"` - ワイドスクリーン

### number_of_images（生成枚数）
- `1`〜`4` の範囲で指定可能
- デフォルトは `4`

### 注意事項
- 安全フィルターは自動的に適用されます（設定不可）
- SynthID電子透かしが自動で追加されます
- 人物生成の制御は現在のAPIでは利用できません

## 💡 Menu Processorでの活用例

1. **メニュー画像生成**: レストランメニューのビジュアル作成
2. **料理画像生成**: メニュー項目の魅力的な画像作成
3. **マスコットキャラクター作成**: レストランのオリジナルキャラクター
4. **プロモーション画像**: SNS用の宣伝画像
5. **メニューデザイン**: 美しいメニューレイアウト

## 🔧 トラブルシューティング

### よくあるエラー

#### APIキーエラー
```
GEMINI_API_KEY が設定されていません
```
**解決方法**: 
- `.env`ファイルに`GEMINI_API_KEY=your_key_here`を追加
- APIキーが正しいか確認

#### インポートエラー
```
ModuleNotFoundError: No module named 'google.genai'
```
**解決方法**:
- `pip install google-genai pillow`を実行
- 仮想環境が有効になっているか確認

#### 有料ティアエラー
```
Imagen 3 is only available on the Paid Tier
```
**解決方法**:
- Google AI Studioで有料ティアにアップグレード
- 請求情報を設定

#### 生成制限エラー
```
Rate limit exceeded
```
**解決方法**:
- リクエスト頻度を下げる
- 少し時間を置いてから再試行

## 🎯 Gemini API vs Vertex AI

| 機能 | Gemini API | Vertex AI |
|------|------------|-----------|
| **セットアップ** | 簡単（APIキーのみ） | 複雑（GCPプロジェクト必要） |
| **認証** | APIキー | サービスアカウント |
| **モデル** | imagen-3.0-generate-002 | imagen-3.0-fast-generate-001 |
| **料金** | 従量課金 | 従量課金 |
| **機能** | 基本的な画像生成 | 高度な編集機能も利用可能 |

## 📚 関連リンク

- [Gemini API ドキュメント](https://ai.google.dev/docs)
- [Google AI Studio](https://aistudio.google.com)
- [Imagen 3 料金](https://ai.google.dev/pricing)
- [Gemini Cookbook](https://github.com/google-gemini/cookbook)

## 🎯 次のステップ

1. `python test_imagen.py`でテストを実行
2. 生成された画像を確認
3. Menu Processorのメイン機能に統合
4. カスタムプロンプトで画像生成をテスト
5. 異なるアスペクト比やスタイルを試す 