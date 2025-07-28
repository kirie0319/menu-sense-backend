"""
MenuEntityテスト
ドメインエンティティのビジネスロジック検証
"""
import pytest

from app_2.domain.entities.menu_entity import MenuEntity


class TestMenuEntity:
    """MenuEntity 単体テスト"""
    
    def test_creation_with_required_fields(self):
        """必須フィールドでの作成テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ"
        )
        
        assert menu.id == "test-001"
        assert menu.name == "Pizza"
        assert menu.translation == "ピザ"
        assert menu.description is None
        assert menu.allergy is None
        assert menu.ingredient is None
        assert menu.search_engine is None
        assert menu.gen_image is None
    
    def test_creation_with_all_fields(self, sample_menu_entity):
        """全フィールドでの作成テスト"""
        menu = sample_menu_entity
        
        assert menu.id == "test-menu-001"
        assert menu.name == "Test Pizza"
        assert menu.translation == "テストピザ"
        assert menu.description == "Delicious test pizza"
        assert menu.allergy == "Contains wheat, dairy"
        assert menu.ingredient == "Flour, cheese, tomato"
        assert menu.search_engine == "[{'title': 'Pizza Image', 'link': 'http://example.com/pizza.jpg'}]"
        assert menu.gen_image == "http://example.com/generated-pizza.jpg"
    
    def test_is_complete_with_complete_entity(self, sample_menu_entity):
        """完全なエンティティの完成度判定テスト"""
        assert sample_menu_entity.is_complete() is True
    
    def test_is_complete_with_missing_id(self):
        """ID欠損時の完成度判定テスト"""
        menu = MenuEntity(
            id="",  # 空のID
            name="Pizza",
            translation="ピザ"
        )
        
        assert menu.is_complete() is False
    
    def test_is_complete_with_missing_name(self):
        """名前欠損時の完成度判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="",  # 空の名前
            translation="ピザ"
        )
        
        assert menu.is_complete() is False
    
    def test_is_complete_with_missing_translation(self):
        """翻訳欠損時の完成度判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation=""  # 空の翻訳
        )
        
        assert menu.is_complete() is False
    
    def test_is_complete_with_none_values(self):
        """None値での完成度判定テスト"""
        menu = MenuEntity(
            id=None,  # None ID
            name="Pizza",
            translation="ピザ"
        )
        
        assert menu.is_complete() is False
    
    def test_has_generated_content_with_description(self):
        """説明付きエンティティの生成コンテンツ判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ",
            description="Delicious pizza"
        )
        
        assert menu.has_generated_content() is True
    
    def test_has_generated_content_with_allergy(self):
        """アレルゲン情報付きエンティティの生成コンテンツ判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ",
            allergy="Contains wheat"
        )
        
        assert menu.has_generated_content() is True
    
    def test_has_generated_content_with_ingredient(self):
        """含有物情報付きエンティティの生成コンテンツ判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ",
            ingredient="Flour, cheese"
        )
        
        assert menu.has_generated_content() is True
    
    def test_has_generated_content_with_multiple_fields(self, sample_menu_entity):
        """複数生成フィールド付きエンティティの判定テスト"""
        assert sample_menu_entity.has_generated_content() is True
    
    def test_has_generated_content_without_content(self):
        """生成コンテンツなしエンティティの判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ"
        )
        
        assert menu.has_generated_content() is False
    
    def test_has_generated_content_with_empty_strings(self):
        """空文字列での生成コンテンツ判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ",
            description="",  # 空文字列
            allergy="",      # 空文字列
            ingredient=""    # 空文字列
        )
        
        assert menu.has_generated_content() is False
    
    def test_has_generated_content_with_none_values(self):
        """None値での生成コンテンツ判定テスト"""
        menu = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ",
            description=None,
            allergy=None,
            ingredient=None
        )
        
        assert menu.has_generated_content() is False
    
    def test_dataclass_immutability(self, sample_menu_entity):
        """データクラスとしての属性アクセステスト"""
        # 属性への読み取りアクセスが可能
        assert sample_menu_entity.id == "test-menu-001"
        assert sample_menu_entity.name == "Test Pizza"
        
        # 属性への書き込みも可能（dataclassのデフォルト動作）
        sample_menu_entity.description = "Updated description"
        assert sample_menu_entity.description == "Updated description"
    
    def test_equality_comparison(self):
        """エンティティの等価比較テスト"""
        menu1 = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ"
        )
        
        menu2 = MenuEntity(
            id="test-001",
            name="Pizza",
            translation="ピザ"
        )
        
        menu3 = MenuEntity(
            id="test-002",  # 異なるID
            name="Pizza",
            translation="ピザ"
        )
        
        assert menu1 == menu2  # 同じ内容
        assert menu1 != menu3  # 異なるID
    
    def test_string_representation(self, sample_menu_entity):
        """文字列表現テスト"""
        str_repr = str(sample_menu_entity)
        
        # dataclassの自動生成される__str__/__repr__をテスト
        assert "MenuEntity" in str_repr
        assert "test-menu-001" in str_repr
        assert "Test Pizza" in str_repr


class TestMenuEntityBusinessLogic:
    """MenuEntity ビジネスロジックテスト"""
    
    def test_complete_and_has_content_combination(self):
        """完成度と生成コンテンツの組み合わせテスト"""
        # 完成していて生成コンテンツもある理想的な状態
        ideal_menu = MenuEntity(
            id="test-001",
            name="Perfect Pizza",
            translation="完璧なピザ",
            description="Amazing pizza",
            allergy="Contains wheat",
            ingredient="Flour, cheese"
        )
        
        assert ideal_menu.is_complete() is True
        assert ideal_menu.has_generated_content() is True
    
    def test_incomplete_but_has_content(self):
        """不完全だが生成コンテンツがある状態"""
        incomplete_menu = MenuEntity(
            id="",  # ID欠損
            name="Pizza",
            translation="ピザ",
            description="Has description but incomplete"
        )
        
        assert incomplete_menu.is_complete() is False
        assert incomplete_menu.has_generated_content() is True
    
    def test_complete_but_no_content(self):
        """完成しているが生成コンテンツがない状態"""
        basic_menu = MenuEntity(
            id="test-001",
            name="Basic Pizza",
            translation="基本ピザ"
        )
        
        assert basic_menu.is_complete() is True
        assert basic_menu.has_generated_content() is False
    
    def test_partial_content_scenarios(self):
        """部分的な生成コンテンツシナリオ"""
        # 説明のみ
        desc_only = MenuEntity(
            id="test-001", name="Pizza", translation="ピザ",
            description="Only description"
        )
        assert desc_only.has_generated_content() is True
        
        # アレルゲンのみ
        allergy_only = MenuEntity(
            id="test-002", name="Pasta", translation="パスタ",
            allergy="Contains wheat"
        )
        assert allergy_only.has_generated_content() is True
        
        # 含有物のみ
        ingredient_only = MenuEntity(
            id="test-003", name="Salad", translation="サラダ",
            ingredient="Lettuce, tomato"
        )
        assert ingredient_only.has_generated_content() is True 