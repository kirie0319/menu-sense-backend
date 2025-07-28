"""
プロンプト管理ユーティリティ (ミニマム版)
YAML基盤でのシンプルなプロンプト管理
"""
from typing import Dict
import yaml
from pathlib import Path
from .utils.logger import get_logger

logger = get_logger("prompt_loader")


class PromptLoader:
    """シンプルなYAML基盤プロンプト管理クラス"""
    
    def __init__(self, base_path: str = "app_2/prompts"):
        """
        プロンプトローダーを初期化
        
        Args:
            base_path: プロンプトファイルのベースパス
        """
        self.base_path = Path(base_path)
        
    def load_prompt(
        self, 
        provider: str, 
        category: str, 
        prompt_name: str
    ) -> Dict[str, str]:
        """
        プロンプトを読み込み
        
        Args:
            provider: AIプロバイダー名 (openai, google)
            category: カテゴリー名 (menu_analysis)
            prompt_name: プロンプト名 (description, allergen, ingredient, categorize)
        
        Returns:
            Dict: プロンプトデータ (system, user)
            
        Raises:
            FileNotFoundError: プロンプトファイルが見つからない場合
        """
        file_path = self.base_path / provider / category / f"{prompt_name}.yaml"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            logger.info(f"Loaded prompt: {provider}/{category}/{prompt_name}")
            return prompt_data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
        
    def format_prompt(self, template: str, **kwargs) -> str:
        """
        テンプレート変数を置換
        
        Args:
            template: プロンプトテンプレート文字列
            **kwargs: 置換する変数
            
        Returns:
            str: 変数が置換されたプロンプト
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise ValueError(f"Missing required variable: {e}")
        
    def get_system_prompt(
        self, 
        provider: str, 
        category: str, 
        prompt_name: str
    ) -> str:
        """
        システムプロンプトを取得
        
        Args:
            provider: AIプロバイダー名
            category: カテゴリー名
            prompt_name: プロンプト名
            
        Returns:
            str: システムプロンプト
        """
        prompt_data = self.load_prompt(provider, category, prompt_name)
        return prompt_data.get("system", "")
        
    def get_user_prompt(
        self, 
        provider: str, 
        category: str, 
        prompt_name: str, 
        **kwargs
    ) -> str:
        """
        ユーザープロンプトを取得（変数置換済み）
        
        Args:
            provider: AIプロバイダー名
            category: カテゴリー名
            prompt_name: プロンプト名
            **kwargs: テンプレート変数
            
        Returns:
            str: 変数置換済みユーザープロンプト
        """
        prompt_data = self.load_prompt(provider, category, prompt_name)
        user_template = prompt_data.get("user", "")
        return self.format_prompt(user_template, **kwargs) 
    
    def load_schema(
        self, 
        provider: str, 
        category: str, 
        schema_name: str
    ) -> Dict[str, any]:
        """
        Function Callingスキーマを読み込み
        
        Args:
            provider: AIプロバイダー名 (openai, google)
            category: カテゴリー名 (menu_analysis)
            schema_name: スキーマ名 (categorize)
        
        Returns:
            Dict: スキーマデータ
            
        Raises:
            FileNotFoundError: スキーマファイルが見つからない場合
        """
        file_path = self.base_path / provider / category / "schemas" / f"{schema_name}.yaml"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                schema_data = yaml.safe_load(f)
            
            logger.info(f"Loaded schema: {provider}/{category}/schemas/{schema_name}")
            return schema_data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
    
    def get_function_schema(
        self,
        provider: str,
        category: str, 
        schema_name: str,
        function_name: str
    ) -> Dict[str, any]:
        """
        特定のFunction Callingスキーマを取得
        
        Args:
            provider: AIプロバイダー名
            category: カテゴリー名
            schema_name: スキーマファイル名
            function_name: 関数名
            
        Returns:
            Dict: Function Callingスキーマ
        """
        schema_data = self.load_schema(provider, category, schema_name)
        function_schema = schema_data.get(function_name)
        
        if not function_schema:
            raise KeyError(f"Function schema '{function_name}' not found in {schema_name}")
        
        return function_schema 