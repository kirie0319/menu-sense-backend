"""
テスト用サンプルデータ

各種テストで使用するサンプルデータを定義します。
"""
from typing import Dict, List, Any


class SampleMenuData:
    """サンプルメニューデータのコレクション"""
    
    # 基本的なメニューテキスト（OCR出力想定）
    SIMPLE_MENU_TEXT = """
    メインディッシュ
    唐揚げ定食 980円
    天ぷら定食 1200円
    親子丼 850円
    
    サイドメニュー
    サラダ 400円
    味噌汁 150円
    
    飲み物
    ビール 500円
    日本酒 800円
    ソフトドリンク 300円
    """
    
    # 複雑なメニューテキスト
    COMPLEX_MENU_TEXT = """
    🍱 お弁当・定食 🍱
    【人気No.1】唐揚げ弁当 ¥980 (税込)
    天ぷら定食 ¥1,200 (エビ天2本、野菜天3種)
    親子丼セット ¥850 (味噌汁・サラダ付き)
    
    🍜 麺類 🍜 
    醤油ラーメン ¥780
    味噌ラーメン ¥820
    つけ麺（大盛り無料） ¥950
    
    🍺 お飲み物 🍺
    生ビール (中) ¥500
    ハイボール ¥450
    日本酒 (一合) ¥800
    ウーロン茶 ¥300
    
    ※価格は全て税込表示
    ※ライス大盛り +¥100
    """
    
    # エラーケース用（読み取りにくいテキスト）
    DIFFICULT_MENU_TEXT = """
    料理名不明 ???円
    ♪♪♪ 特別メニュー ♪♪♪
    🔥激辛🔥チャレンジメニュー 時価
    
    お得セット
    A定食 900
    B定食 1000
    C定食 1100
    """
    
    # 多言語混在メニュー
    MULTILINGUAL_MENU_TEXT = """
    Japanese Cuisine 日本料理
    Sushi 寿司 ¥500～
    Tempura 天ぷら ¥800
    Ramen ラーメン ¥750
    
    Western Food 洋食
    Hamburger ハンバーガー ¥650
    Pizza ピザ ¥1200
    Pasta パスタ ¥900
    
    Drinks 飲み物
    Beer ビール ¥500
    Wine ワイン ¥600/glass
    Coffee コーヒー ¥300
    """


class SampleCategoryData:
    """サンプルカテゴリ分類データ"""
    
    BASIC_CATEGORIES = {
        "メインディッシュ": [
            {"name": "唐揚げ定食", "price": "980円"},
            {"name": "天ぷら定食", "price": "1200円"},
            {"name": "親子丼", "price": "850円"}
        ],
        "サイドメニュー": [
            {"name": "サラダ", "price": "400円"},
            {"name": "味噌汁", "price": "150円"}
        ],
        "飲み物": [
            {"name": "ビール", "price": "500円"},
            {"name": "日本酒", "price": "800円"},
            {"name": "ソフトドリンク", "price": "300円"}
        ]
    }
    
    COMPLEX_CATEGORIES = {
        "お弁当・定食": [
            {"name": "唐揚げ弁当", "price": "¥980", "note": "税込"},
            {"name": "天ぷら定食", "price": "¥1,200", "note": "エビ天2本、野菜天3種"},
            {"name": "親子丼セット", "price": "¥850", "note": "味噌汁・サラダ付き"}
        ],
        "麺類": [
            {"name": "醤油ラーメン", "price": "¥780"},
            {"name": "味噌ラーメン", "price": "¥820"},
            {"name": "つけ麺", "price": "¥950", "note": "大盛り無料"}
        ],
        "お飲み物": [
            {"name": "生ビール", "price": "¥500", "note": "中"},
            {"name": "ハイボール", "price": "¥450"},
            {"name": "日本酒", "price": "¥800", "note": "一合"},
            {"name": "ウーロン茶", "price": "¥300"}
        ]
    }


class SampleTranslationData:
    """サンプル翻訳データ"""
    
    TRANSLATED_MENU = {
        "Main Dishes": [
            {
                "japanese_name": "唐揚げ定食",
                "english_name": "Fried Chicken Set",
                "price": "980円"
            },
            {
                "japanese_name": "天ぷら定食",
                "english_name": "Tempura Set",
                "price": "1200円"
            },
            {
                "japanese_name": "親子丼",
                "english_name": "Chicken and Egg Rice Bowl",
                "price": "850円"
            }
        ],
        "Side Dishes": [
            {
                "japanese_name": "サラダ",
                "english_name": "Salad",
                "price": "400円"
            },
            {
                "japanese_name": "味噌汁",
                "english_name": "Miso Soup",
                "price": "150円"
            }
        ],
        "Drinks": [
            {
                "japanese_name": "ビール",
                "english_name": "Beer",
                "price": "500円"
            },
            {
                "japanese_name": "日本酒",
                "english_name": "Sake",
                "price": "800円"
            },
            {
                "japanese_name": "ソフトドリンク",
                "english_name": "Soft Drink",
                "price": "300円"
            }
        ]
    }


class SampleDescriptionData:
    """サンプル説明付きデータ"""
    
    MENU_WITH_DESCRIPTIONS = {
        "Main Dishes": [
            {
                "japanese_name": "唐揚げ定食",
                "english_name": "Fried Chicken Set",
                "price": "980円",
                "description": "Crispy Japanese-style fried chicken pieces served with steamed rice, miso soup, and pickled vegetables. A popular comfort food that's perfectly seasoned with soy sauce and garlic."
            },
            {
                "japanese_name": "天ぷら定食",
                "english_name": "Tempura Set",
                "price": "1200円",
                "description": "Assorted tempura featuring fresh shrimp and seasonal vegetables, lightly battered and fried to golden perfection. Served with tentsuyu dipping sauce, rice, and miso soup."
            },
            {
                "japanese_name": "親子丼",
                "english_name": "Chicken and Egg Rice Bowl",
                "price": "850円",
                "description": "Traditional Japanese rice bowl topped with tender chicken and fluffy scrambled eggs simmered in a sweet and savory dashi-based sauce. Garnished with fresh scallions."
            }
        ],
        "Side Dishes": [
            {
                "japanese_name": "サラダ",
                "english_name": "Salad",
                "price": "400円",
                "description": "Fresh mixed greens with seasonal vegetables, served with your choice of Japanese sesame dressing or vinaigrette."
            },
            {
                "japanese_name": "味噌汁",
                "english_name": "Miso Soup",
                "price": "150円",
                "description": "Traditional Japanese soup made from fermented soybean paste, typically served with tofu, wakame seaweed, and scallions."
            }
        ],
        "Drinks": [
            {
                "japanese_name": "ビール",
                "english_name": "Beer",
                "price": "500円",
                "description": "Crisp Japanese draft beer, perfectly chilled and refreshing. A great accompaniment to any meal."
            },
            {
                "japanese_name": "日本酒",
                "english_name": "Sake",
                "price": "800円",
                "description": "Premium Japanese rice wine with a smooth, clean taste. Served either warm or chilled according to your preference."
            },
            {
                "japanese_name": "ソフトドリンク",
                "english_name": "Soft Drink",
                "price": "300円",
                "description": "Selection of non-alcoholic beverages including cola, orange juice, and iced tea."
            }
        ]
    }


class TestImageData:
    """テスト用画像データ"""
    
    # Base64エンコードされたテスト用の小さな画像データ（1x1 pixel PNG）
    TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    # 複数の画像サイズのメタデータ
    IMAGE_METADATA = {
        "small": {"width": 100, "height": 100, "format": "JPEG"},
        "medium": {"width": 800, "height": 600, "format": "JPEG"},
        "large": {"width": 1920, "height": 1080, "format": "JPEG"},
        "portrait": {"width": 600, "height": 800, "format": "JPEG"},
        "landscape": {"width": 1200, "height": 800, "format": "JPEG"}
    }


class ErrorTestData:
    """エラーテスト用データ"""
    
    # 各種エラーケース
    API_ERRORS = {
        "connection_timeout": {
            "error": "Connection timeout",
            "code": "TIMEOUT",
            "retry_able": True
        },
        "invalid_api_key": {
            "error": "Invalid API key",
            "code": "AUTH_ERROR", 
            "retry_able": False
        },
        "quota_exceeded": {
            "error": "Quota exceeded",
            "code": "QUOTA_ERROR",
            "retry_able": True
        },
        "service_unavailable": {
            "error": "Service temporarily unavailable",
            "code": "SERVICE_ERROR",
            "retry_able": True
        }
    }
    
    # 不正なデータ形式
    INVALID_DATA_FORMATS = {
        "empty_string": "",
        "null_value": None,
        "invalid_json": "{ invalid json }",
        "wrong_structure": {"wrong": "structure"},
        "missing_required_fields": {"categories": {}},  # uncategorizedが欠如
        "invalid_types": {"categories": "string_instead_of_dict", "uncategorized": {}},
    }


class PerformanceTestData:
    """パフォーマンステスト用データ"""
    
    # 異なるサイズのテストデータ
    SMALL_DATASET = {
        "menu_items": 5,
        "categories": 2,
        "expected_processing_time": 1.0  # 秒
    }
    
    MEDIUM_DATASET = {
        "menu_items": 20,
        "categories": 5,
        "expected_processing_time": 3.0  # 秒
    }
    
    LARGE_DATASET = {
        "menu_items": 100,
        "categories": 10,
        "expected_processing_time": 10.0  # 秒
    }
    
    # 並行処理テスト用
    CONCURRENT_SESSIONS = [f"session-{i}" for i in range(10)]


def get_sample_menu_by_complexity(complexity: str = "simple") -> str:
    """複雑さに応じたサンプルメニューを取得"""
    if complexity == "simple":
        return SampleMenuData.SIMPLE_MENU_TEXT
    elif complexity == "complex":
        return SampleMenuData.COMPLEX_MENU_TEXT
    elif complexity == "difficult":
        return SampleMenuData.DIFFICULT_MENU_TEXT
    elif complexity == "multilingual":
        return SampleMenuData.MULTILINGUAL_MENU_TEXT
    else:
        return SampleMenuData.SIMPLE_MENU_TEXT


def get_expected_categories_by_complexity(complexity: str = "simple") -> Dict[str, List[Dict[str, Any]]]:
    """複雑さに応じた期待されるカテゴリを取得"""
    if complexity == "simple":
        return SampleCategoryData.BASIC_CATEGORIES
    elif complexity == "complex":
        return SampleCategoryData.COMPLEX_CATEGORIES
    else:
        return SampleCategoryData.BASIC_CATEGORIES


def create_test_image_bytes(size: str = "small") -> bytes:
    """テスト用画像のバイトデータを作成"""
    import base64
    # 実際のプロジェクトでは、Pillowを使用して画像を生成することも可能
    return base64.b64decode(TestImageData.TINY_PNG_BASE64) 