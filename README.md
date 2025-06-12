# 🍜 Japanese Restaurant Menu Translator

日本語のレストランメニューを写真から読み取り、外国人観光客にとってわかりやすい詳細な英語説明付きで翻訳するFastAPIアプリケーションです。

## 🚀 特徴

- **画像アップロード**: ドラッグ&ドロップまたはクリックで簡単にメニュー画像をアップロード
- **高精度テキスト抽出**: Google Vision APIを使用した高精度な日本語テキスト抽出
- **AI翻訳**: OpenAI GPTを使用した文脈を理解した自然な翻訳
- **詳細な説明**: 単純な翻訳ではなく、調理法、食材、味の特徴などの詳細な説明を追加
- **美しいUI**: モダンでレスポンシブなWebインターフェース
- **2段階処理**: テキスト抽出結果も表示し、翻訳プロセスが透明

## 📋 要件

- Python 3.8+
- OpenAI API キー
- Google Cloud Project with Vision API enabled
- Google Cloud Service Account Key

## 🛠️ セットアップ

### 1. プロジェクトのクローン

```bash
git clone <repository-url>
cd restaurant
```

### 2. 仮想環境の作成と有効化

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. Google Cloud Setupの設定

#### 4.1 Google Cloud Projectの作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成またはを既存のプロジェクトを選択
3. Vision APIを有効化

#### 4.2 Service Accountの作成
1. IAM & Admin > Service Accounts
2. 「Create Service Account」をクリック
3. 適切な名前を設定し、「Cloud Vision API User」ロールを付与
4. JSONキーを作成してダウンロード

### 5. 環境変数の設定

`.env`ファイルを作成し、API キーを設定してください：

```bash
cp env_example.txt .env
```

`.env`ファイルを編集：

```
OPENAI_API_KEY=your_actual_openai_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

## 🚀 使用方法

### アプリケーションの起動

```bash
python main.py
```

または

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### アクセス

ブラウザで以下のURLにアクセスしてください：

```
http://localhost:8000
```

### 使い方

1. メインページにアクセス
2. 日本語メニューの写真をアップロード（ドラッグ&ドロップまたはクリック）
3. Google Vision APIによるテキスト抽出とAI翻訳の完了を待つ
4. 抽出されたテキストと詳細な英語説明付きの翻訳結果を確認

## 📝 API エンドポイント

### メイン画面
- `GET /` - メインのWebインターフェース

### 翻訳
- `POST /translate` - 画像ファイルをアップロードしてテキスト抽出と翻訳を実行
  - パラメータ: `file` (multipart/form-data)
  - レスポンス: JSON形式の抽出テキストと翻訳結果

### ヘルスチェック
- `GET /health` - アプリケーションの状態確認

## 📊 レスポンス形式

```json
{
  "extracted_text": "焼き鳥 300円\n天ぷら 500円\n寿司 800円",
  "menu_items": [
    {
      "japanese_name": "焼き鳥",
      "english_name": "Yakitori",
      "description": "Traditional Japanese grilled chicken skewers, marinated in savory tare sauce and grilled over charcoal for a smoky flavor. Served with various cuts including thigh, breast, and liver.",
      "price": "¥300"
    },
    {
      "japanese_name": "天ぷら",
      "english_name": "Tempura",
      "description": "Light and crispy battered and deep-fried seafood and vegetables, served with tentsuyu dipping sauce made from dashi, soy sauce, and mirin.",
      "price": "¥500"
    }
  ]
}
```

## 🔧 技術スタック

- **Backend**: FastAPI
- **Text Extraction**: Google Cloud Vision API
- **AI Translation**: OpenAI GPT-4
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Image Processing**: Pillow
- **File Handling**: aiofiles

## 📄 処理フロー

1. **画像アップロード**: ユーザーがメニュー画像をアップロード
2. **テキスト抽出**: Google Vision APIで日本語テキストを高精度で抽出
3. **AI翻訳**: 抽出されたテキストをOpenAI GPTで文脈を理解して翻訳
4. **結果表示**: 抽出テキストと詳細説明付きの英語翻訳を表示

## 📄 例

### 入力
日本語メニューの写真（例：焼き鳥、天ぷら、寿司など）

### 処理
1. **Google Vision API**: 画像から「焼き鳥 300円」などのテキストを抽出
2. **OpenAI GPT**: 抽出されたテキストを詳細説明付きで翻訳

### 出力
- **焼き鳥** → **Yakitori** - Traditional Japanese grilled chicken skewers, marinated in savory tare sauce and grilled over charcoal for a smoky flavor
- **天ぷら** → **Tempura** - Light and crispy battered and deep-fried seafood and vegetables, served with tentsuyu dipping sauce
- **寿司** → **Sushi** - Fresh raw fish served on seasoned rice, prepared by skilled sushi chefs using traditional techniques

## ⚠️ 注意事項

- OpenAI API キーが必要です
- Google Cloud Project と Vision API の設定が必要です
- API使用料金が発生する可能性があります（Google Vision API + OpenAI API）
- 画像の品質により抽出精度が変わる場合があります
- インターネット接続が必要です

## 🤝 貢献

プルリクエストや課題報告は歓迎です。大きな変更を行う前に、まずissueを開いて議論してください。

## 🔍 Google Search APIテスト

Google Search APIの出力をテストするための専用ツールも提供しています：

### Web UIでのテスト

```bash
python google_search_test.py --web
```

ブラウザで `http://localhost:8001` にアクセスして、Googleの画像検索とテキスト検索をテストできます。

### コマンドラインでのテスト

```bash
# セットアップ確認
python test_google_search.py --check

# 画像検索のテスト
python test_google_search.py --image "焼き鳥"

# テキスト検索のテスト
python test_google_search.py --text "Japanese cuisine yakitori"

# インタラクティブモード
python test_google_search.py --interactive
```

### 機能

- **画像検索**: 日本語/英語のキーワードで画像検索
- **テキスト検索**: ウェブ検索結果の表示
- **詳細情報**: 画像サイズ、ソース、サムネイルなどの詳細情報表示
- **モーダル表示**: 画像のフルサイズ表示
- **言語フィルター**: 検索結果の言語を指定可能

## 📜 ライセンス

このプロジェクトはMITライセンスの下で公開されています。 