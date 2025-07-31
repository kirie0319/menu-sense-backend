# OCR結果 & マッピングテストデータ

このディレクトリには、OCRエンドポイントのテスト結果と、マッピング処理のテスト用データが含まれています。

## 📂 ファイル構成

### 🖼️ **元画像ファイル**
- `menu_test.webp` - カフェメニュー画像 (260KB)
- `menu_test2.jpg` - 居酒屋メニュー画像 (165KB)

### 📋 **OCR完全結果**
- `ocr_result_menu_test_webp.json` - カフェメニューの完全OCR結果
- `ocr_result_menu_test2_jpg.json` - 居酒屋メニューの完全OCR結果

### 🗺️ **マッピング処理テスト用データ**
- `mapping_test_data_cafe.json` - カフェメニューのマッピング用データ
- `mapping_test_data_izakaya.json` - 居酒屋メニューのマッピング用データ

## 📊 **データ詳細**

### **カフェメニュー (`menu_test.webp`)**
```json
{
  "処理時間": "0.345秒",
  "抽出要素数": 30,
  "メニュー種類": ["COFFEE", "TEA", "JUICE", "DESSERT"],
  "価格帯": "¥400-¥600"
}
```

### **居酒屋メニュー (`menu_test2.jpg`)**
```json
{
  "処理時間": "0.34秒", 
  "抽出要素数": 94,
  "メニュー種類": ["やきとり", "サラダ", "お酒", "揚げ物", "デザート", "ソフトドリンク"],
  "価格帯": "¥200-¥700"
}
```

## 🧪 **テスト用途**

### **1. マッピング処理テスト**
```python
# テストデータの読み込み例
import json

with open('mapping_test_data_cafe.json', 'r', encoding='utf-8') as f:
    cafe_ocr_data = json.load(f)

# マッピングサービスでテスト
from app_2.services.mapping_service import get_menu_mapping_categorize_service
mapping_service = get_menu_mapping_categorize_service()
formatted_data = mapping_service._format_mapping_data(cafe_ocr_data)
```

### **2. カテゴライズ処理テスト**
```python
# マッピング結果でカテゴライズテスト
categorize_result = await mapping_service.categorize_mapping_data(
    cafe_ocr_data, level="paragraph"
)
```

### **3. 処理時間ベンチマーク**
```python
# OCR → Mapping → Categorize の段階別処理時間測定
import time

# 1. OCR段階 (実測値)
ocr_time = 0.345  # seconds

# 2. Mapping段階 (テスト対象)
start = time.time()
formatted_data = mapping_service._format_mapping_data(cafe_ocr_data)
mapping_time = time.time() - start

# 3. Categorize段階 (テスト対象)
start = time.time()
categorize_result = await categorize_service.categorize_menu_structure(
    formatted_data, "paragraph"
)
categorize_time = time.time() - start

print(f"OCR: {ocr_time:.3f}s")
print(f"Mapping: {mapping_time:.3f}s") 
print(f"Categorize: {categorize_time:.3f}s")
print(f"Total: {ocr_time + mapping_time + categorize_time:.3f}s")
```

## 🎯 **期待される結果**

### **パフォーマンス目標**
- **OCR**: ✅ 0.3-1.0秒 (達成済み)
- **Mapping**: 🎯 <0.1秒 (軽量処理)
- **Categorize**: ⚠️ <5秒 (現在の問題箇所)

### **データ品質確認**
- 座標情報の正確性
- テキスト抽出の完全性
- 価格とメニュー名の正しい分離
- カテゴリ判定の妥当性

## 🚀 **使用例**

### **マッピングエンドポイント作成時**
これらのテストデータを使用して、マッピング処理の単体エンドポイントを作成し、処理時間を測定できます。

### **カテゴライズエンドポイント作成時**
フォーマット済みマッピングデータを使用して、OpenAI Categorize処理の単体テストが可能です。

### **パフォーマンス最適化**
各段階の処理時間を個別に測定することで、48秒問題のボトルネック特定に活用できます。