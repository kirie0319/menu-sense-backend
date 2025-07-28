"""
OpenAI Base Client - Infrastructure Layer
Base functionality for OpenAI API integration with Function Calling support
"""
import json
import asyncio
from typing import Dict, List, Any
try:
    from openai import AsyncOpenAI
    import openai
except ImportError:
    AsyncOpenAI = None
    openai = None

from app_2.core.config import settings
from app_2.utils.logger import get_logger
from app_2.prompt_loader import PromptLoader

logger = get_logger("openai_base")


class OpenAIBaseClient:
    """
    OpenAI API 基底クライアント
    
    Function Calling対応の共通設定・API呼び出し機能を提供
    """
    
    def __init__(self):
        """
        OpenAI API 基底クライアントを初期化
        """
        if not AsyncOpenAI:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            self.client = None
        elif not settings.ai.openai_api_key:
            logger.warning("OPENAI_API_KEY not set")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=settings.ai.openai_api_key,
                timeout=settings.ai.openai_timeout,
                max_retries=settings.ai.openai_max_retries
            )
        
        self.prompt_loader = PromptLoader()

    def is_available(self) -> bool:
        """OpenAI APIが利用可能かチェック"""
        return self.client is not None and bool(settings.ai.openai_api_key)

    async def _make_function_call_request(
        self,
        system_prompt: str,
        user_prompt: str,
        functions: List[Dict[str, Any]],
        function_call: Dict[str, str],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        OpenAI Function Calling API への共通リクエスト処理
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト  
            functions: Function Callingのスキーマ定義
            function_call: 呼び出す関数の指定
            max_retries: 最大リトライ回数
            
        Returns:
            Dict[str, Any]: パースされたFunction Callingの結果
            
        Raises:
            Exception: API 呼び出し失敗時
        """
        if not self.is_available():
            raise Exception("OpenAI API is not available")

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.ai.openai_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    functions=functions,
                    function_call=function_call
                )
                
                # Function Callingの結果をパース
                function_call_result = response.choices[0].message.function_call
                if function_call_result and function_call_result.arguments:
                    result = json.loads(function_call_result.arguments)
                    logger.info(f"Function call successful: {function_call_result.name}")
                    return result
                else:
                    raise ValueError("Function call not found in response")
                    
            except openai.RateLimitError as e:
                if attempt == max_retries:
                    raise Exception(f"Rate limit exceeded after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                if attempt == max_retries:
                    raise Exception(f"API error after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"API error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse function call result: {e}")
                raise Exception(f"Invalid JSON response from OpenAI: {str(e)}")
                
            except Exception as e:
                logger.error(f"OpenAI API request failed: {e}")
                raise Exception(f"OpenAI API error: {str(e)}")

    async def _make_completion_request(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> str:
        """
        従来型のChat Completions API呼び出し（後方互換性用）
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト  
            max_tokens: 最大トークン数
            temperature: 創造性パラメータ
            
        Returns:
            str: API レスポンス内容
            
        Raises:
            Exception: API 呼び出し失敗時
        """
        if not self.is_available():
            raise Exception("OpenAI API is not available")

        try:
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise

    def _get_prompts(
        self,
        prompt_name: str,
        menu_item: str,
        category: str = ""
    ) -> tuple[str, str]:
        """
        プロンプトローダーからプロンプトを取得
        
        Args:
            prompt_name: プロンプト名
            menu_item: メニュー項目
            category: カテゴリ（オプション）
            
        Returns:
            tuple[str, str]: (system_prompt, user_prompt)
        """
        prompts = self.prompt_loader.load_prompt(
            "openai", "menu_analysis", prompt_name
        )
        
        system_prompt = prompts.get("system", "")
        user_template = prompts.get("user", "")
        
        # デバッグ用ログ
        logger.debug(f"Raw user template: {user_template}")
        logger.debug(f"Available format keys: menu_item='{menu_item}', category='{category}'")
        
        try:
            user_prompt = user_template.format(menu_item=menu_item, category=category)
        except KeyError as e:
            logger.error(f"Template formatting error. Missing key: {e}")
            logger.error(f"Template requires keys: {e}, but menu_item='{menu_item}', category='{category}' provided")
            # フォールバック: 利用可能なキーのみで置換
            try:
                user_prompt = user_template.format(menu_item=menu_item)
            except KeyError:
                # 最終フォールバック: 単純に文字列置換
                user_prompt = user_template.replace("{menu_item}", menu_item).replace("{category}", category)
        
        return system_prompt, user_prompt 