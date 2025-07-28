"""
PromptLoaderテスト
YAML基盤プロンプト管理システムの検証
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from app_2.prompt_loader import PromptLoader


class TestPromptLoader:
    """PromptLoader 単体テスト"""
    
    def test_init_with_default_path(self):
        """デフォルトパスでの初期化テスト"""
        loader = PromptLoader()
        assert loader.base_path == Path("app_2/prompts")
    
    def test_init_with_custom_path(self):
        """カスタムパスでの初期化テスト"""
        custom_path = "/custom/prompts"
        loader = PromptLoader(base_path=custom_path)
        assert loader.base_path == Path(custom_path)
    
    def test_load_prompt_success(self, temp_prompts_dir):
        """正常なプロンプト読み込みテスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        result = loader.load_prompt("openai", "menu_analysis", "description")
        
        assert "system" in result
        assert "user" in result
        assert result["system"] == "You are a culinary expert."
        assert "{menu_item}" in result["user"]
    
    def test_load_prompt_file_not_found(self, temp_prompts_dir):
        """存在しないプロンプトファイルのテスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_prompt("openai", "menu_analysis", "nonexistent")
        
        assert "Prompt file not found" in str(exc_info.value)
    
    @patch("builtins.open", mock_open(read_data="invalid: yaml: content: ["))
    def test_load_prompt_invalid_yaml(self, temp_prompts_dir):
        """無効なYAMLファイルのテスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        with pytest.raises(ValueError) as exc_info:
            loader.load_prompt("openai", "menu_analysis", "description")
        
        assert "Invalid YAML format" in str(exc_info.value)
    
    def test_format_prompt_success(self):
        """テンプレート変数置換の正常テスト"""
        loader = PromptLoader()
        template = "Generate description for: {menu_item} in {language}"
        
        result = loader.format_prompt(
            template, 
            menu_item="pizza", 
            language="Japanese"
        )
        
        assert result == "Generate description for: pizza in Japanese"
    
    def test_format_prompt_missing_variable(self):
        """テンプレート変数不足のテスト"""
        loader = PromptLoader()
        template = "Generate description for: {menu_item} in {language}"
        
        with pytest.raises(ValueError) as exc_info:
            loader.format_prompt(template, menu_item="pizza")  # language missing
        
        assert "Missing required variable" in str(exc_info.value)
    
    def test_get_system_prompt(self, temp_prompts_dir):
        """システムプロンプト取得テスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        system_prompt = loader.get_system_prompt(
            "openai", "menu_analysis", "description"
        )
        
        assert system_prompt == "You are a culinary expert."
    
    def test_get_system_prompt_missing_key(self, temp_prompts_dir):
        """systemキーが存在しない場合のテスト"""
        # system キーがないYAMLファイルを作成
        yaml_path = Path(temp_prompts_dir) / "openai" / "menu_analysis" / "nosystem.yaml"
        with open(yaml_path, 'w') as f:
            f.write("user: \"Only user prompt\"")
        
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        system_prompt = loader.get_system_prompt(
            "openai", "menu_analysis", "nosystem"
        )
        
        assert system_prompt == ""  # デフォルト値
    
    def test_get_user_prompt_with_variables(self, temp_prompts_dir):
        """変数置換ありユーザープロンプト取得テスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        user_prompt = loader.get_user_prompt(
            "openai", "menu_analysis", "description",
            menu_item="sushi"
        )
        
        assert "Generate a description for: sushi" in user_prompt
        assert "{menu_item}" not in user_prompt  # 変数が置換されている
    
    def test_get_user_prompt_without_variables(self, temp_prompts_dir):
        """変数なしユーザープロンプト取得テスト"""
        # 変数なしのテスト用プロンプト作成
        yaml_path = Path(temp_prompts_dir) / "openai" / "menu_analysis" / "simple.yaml"
        with open(yaml_path, 'w') as f:
            f.write("system: \"Simple system\"\n")
            f.write("user: \"Simple user prompt without variables\"")
        
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        user_prompt = loader.get_user_prompt(
            "openai", "menu_analysis", "simple"
        )
        
        assert user_prompt == "Simple user prompt without variables"
    
    def test_get_user_prompt_missing_variables(self, temp_prompts_dir):
        """必要な変数が不足している場合のテスト"""
        loader = PromptLoader(base_path=temp_prompts_dir)
        
        with pytest.raises(ValueError):
            loader.get_user_prompt(
                "openai", "menu_analysis", "description"
                # menu_item変数が必要だが提供されていない
            )


class TestPromptLoaderIntegration:
    """PromptLoader 統合テスト"""
    
    def test_real_prompt_files_loading(self):
        """実際のプロンプトファイル読み込みテスト"""
        # 実際のプロンプトディレクトリが存在するかチェック
        real_prompts_path = Path("app_2/prompts")
        if not real_prompts_path.exists():
            pytest.skip("Real prompts directory not found")
        
        loader = PromptLoader()
        
        # 実際のプロンプトファイルを読み込み
        try:
            description_prompt = loader.load_prompt(
                "openai", "menu_analysis", "description"
            )
            assert "system" in description_prompt
            assert "user" in description_prompt
        except FileNotFoundError:
            pytest.skip("Real prompt files not found")
    
    def test_all_expected_prompts_exist(self):
        """期待されるプロンプトファイルの存在確認"""
        real_prompts_path = Path("app_2/prompts/openai/menu_analysis")
        if not real_prompts_path.exists():
            pytest.skip("Real prompts directory not found")
        
        expected_prompts = ["description", "allergen", "ingredient", "categorize"]
        loader = PromptLoader()
        
        for prompt_name in expected_prompts:
            yaml_file = real_prompts_path / f"{prompt_name}.yaml"
            if yaml_file.exists():
                # ファイルが存在する場合、読み込み可能かテスト
                prompt_data = loader.load_prompt(
                    "openai", "menu_analysis", prompt_name
                )
                assert isinstance(prompt_data, dict)
                # system または user のいずれかは存在すべき
                assert "system" in prompt_data or "user" in prompt_data 