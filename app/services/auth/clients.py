"""
APIクライアント管理サービス
"""
from typing import Optional, Any, Dict
from .credentials import get_credentials_manager

class APIClientsManager:
    """APIクライアントを管理するシングルトンクラス"""
    
    _instance: Optional['APIClientsManager'] = None
    
    def __new__(cls) -> 'APIClientsManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 認証情報マネージャー
        self.credentials_manager = get_credentials_manager()
        
        # APIクライアント
        self.vision_client = None
        self.translate_client = None
        self.openai_client = None
        self.gemini_model = None
        self.imagen_client = None
        
        # 可用性フラグ
        self.VISION_AVAILABLE = False
        self.TRANSLATE_AVAILABLE = False
        self.OPENAI_AVAILABLE = False
        self.GEMINI_AVAILABLE = False
        self.IMAGEN_AVAILABLE = False
        
        # クライアントを初期化
        self._initialize_clients()
        self._initialized = True
    
    def _initialize_clients(self) -> None:
        """すべてのAPIクライアントを初期化"""
        self._initialize_google_vision()
        self._initialize_google_translate()
        self._initialize_openai()
        self._initialize_gemini()
        self._initialize_imagen3()
    
    def _initialize_google_vision(self) -> None:
        """Google Vision APIクライアントを初期化"""
        try:
            from google.cloud import vision
            
            credentials = self.credentials_manager.get_google_credentials()
            if credentials:
                self.vision_client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                self.vision_client = vision.ImageAnnotatorClient()  # デフォルト認証を試行
            
            self.VISION_AVAILABLE = True
            print("✅ Google Vision API client initialized successfully")
        except Exception as e:
            self.VISION_AVAILABLE = False
            print(f"❌ Google Vision API initialization failed: {e}")
            self.vision_client = None
    
    def _initialize_google_translate(self) -> None:
        """Google Translate APIクライアントを初期化"""
        try:
            from google.cloud import translate_v2 as translate
            
            credentials = self.credentials_manager.get_google_credentials()
            if credentials:
                self.translate_client = translate.Client(credentials=credentials)
            else:
                self.translate_client = translate.Client()  # デフォルト認証を試行
            
            self.TRANSLATE_AVAILABLE = True
            print("✅ Google Translate API client initialized successfully")
        except Exception as e:
            self.TRANSLATE_AVAILABLE = False
            self.translate_client = None
            print(f"❌ Google Translate API initialization failed: {e}")
            print("   Note: Install with 'pip install google-cloud-translate' and set up authentication")
    
    def _initialize_openai(self) -> None:
        """OpenAI APIクライアントを初期化"""
        try:
            import openai
            from openai import AsyncOpenAI
            from app.core.config import settings
            
            self.OPENAI_AVAILABLE = bool(settings.OPENAI_API_KEY)
            
            if self.OPENAI_AVAILABLE:
                # AsyncOpenAIクライアントを初期化（タイムアウトとリトライ設定付き）
                self.openai_client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=settings.OPENAI_TIMEOUT,
                    max_retries=settings.OPENAI_MAX_RETRIES
                )
            
            print(f"{'✅' if self.OPENAI_AVAILABLE else '❌'} OpenAI API {'configured' if self.OPENAI_AVAILABLE else 'not configured'}")
        except Exception as e:
            self.OPENAI_AVAILABLE = False
            self.openai_client = None
            print(f"❌ OpenAI API initialization failed: {e}")
    
    def _initialize_gemini(self) -> None:
        """Gemini APIクライアントを初期化"""
        try:
            import google.generativeai as genai
            from app.core.config import settings
            
            self.GEMINI_AVAILABLE = bool(settings.GEMINI_API_KEY)
            
            if self.GEMINI_AVAILABLE:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Gemini 2.0 Flash modelを使用
                self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
                print("✅ Gemini 2.0 Flash API configured successfully")
            else:
                self.gemini_model = None
                print("⚠️ GEMINI_API_KEY not found in environment variables")
            
        except ImportError:
            self.GEMINI_AVAILABLE = False
            self.gemini_model = None
            print("❌ google-generativeai package not installed. Install with: pip install google-generativeai")
        except Exception as e:
            self.GEMINI_AVAILABLE = False
            self.gemini_model = None
            print(f"❌ Gemini API initialization failed: {e}")
    
    def _initialize_imagen3(self) -> None:
        """Imagen 3 APIクライアントを初期化"""
        try:
            from google import genai as imagen_genai
            from app.core.config import settings
            
            self.IMAGEN_AVAILABLE = bool(settings.GEMINI_API_KEY) and settings.IMAGE_GENERATION_ENABLED
            
            if self.IMAGEN_AVAILABLE:
                self.imagen_client = imagen_genai.Client(api_key=settings.GEMINI_API_KEY)
                print("✅ Imagen 3 (Gemini API) configured successfully")
            else:
                self.imagen_client = None
                print("⚠️ Imagen 3 not available - GEMINI_API_KEY required")
            
        except ImportError:
            self.IMAGEN_AVAILABLE = False
            self.imagen_client = None
            print("❌ google-genai package not installed for Imagen 3. Install with: pip install google-genai")
        except Exception as e:
            self.IMAGEN_AVAILABLE = False
            self.imagen_client = None
            print(f"❌ Imagen 3 initialization failed: {e}")
    
    # クライアント取得メソッド
    def get_vision_client(self):
        """Google Vision APIクライアントを取得"""
        return self.vision_client
    
    def get_translate_client(self):
        """Google Translate APIクライアントを取得"""
        return self.translate_client
    
    def get_openai_client(self):
        """OpenAI APIクライアントを取得"""
        return self.openai_client
    
    def get_gemini_model(self):
        """Gemini APIモデルを取得"""
        return self.gemini_model
    
    def get_imagen_client(self):
        """Imagen 3 APIクライアントを取得"""
        return self.imagen_client
    
    def get_google_credentials(self):
        """Google Cloud認証情報を取得"""
        return self.credentials_manager.get_google_credentials()
    
    # 可用性チェックメソッド
    def is_vision_available(self) -> bool:
        return self.VISION_AVAILABLE
    
    def is_translate_available(self) -> bool:
        return self.TRANSLATE_AVAILABLE
    
    def is_openai_available(self) -> bool:
        return self.OPENAI_AVAILABLE
    
    def is_gemini_available(self) -> bool:
        return self.GEMINI_AVAILABLE
    
    def is_imagen_available(self) -> bool:
        return self.IMAGEN_AVAILABLE
    
    def get_availability_status(self) -> Dict[str, bool]:
        """すべてのAPIの可用性ステータスを取得"""
        return {
            "VISION_AVAILABLE": self.VISION_AVAILABLE,
            "TRANSLATE_AVAILABLE": self.TRANSLATE_AVAILABLE,
            "OPENAI_AVAILABLE": self.OPENAI_AVAILABLE,
            "GEMINI_AVAILABLE": self.GEMINI_AVAILABLE,
            "IMAGEN_AVAILABLE": self.IMAGEN_AVAILABLE
        }

# シングルトンインスタンスを取得する関数
def get_api_clients_manager() -> APIClientsManager:
    """APIClientsManagerのシングルトンインスタンスを取得"""
    return APIClientsManager() 