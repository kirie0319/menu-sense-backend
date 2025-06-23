import io
import json
from typing import Optional
from google.cloud import vision
from google.oauth2 import service_account

from app.core.config import settings
from .base import BaseOCRService, OCRResult

class GoogleVisionOCRService(BaseOCRService):
    """Google Vision APIを使用したOCRサービス"""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.credentials = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Google Vision APIクライアントを初期化"""
        try:
            # 統一管理されたCredentialsManagerを使用
            from app.services.auth.credentials import get_credentials_manager
            
            credentials_manager = get_credentials_manager()
            self.credentials = credentials_manager.get_google_credentials()
            
            if self.credentials:
                self.client = vision.ImageAnnotatorClient(credentials=self.credentials)
                print("✅ Google Vision API client initialized with unified credentials")
            else:
                # デフォルト認証を試行
                try:
                    self.client = vision.ImageAnnotatorClient()
                    print("✅ Google Vision API client initialized with default credentials")
                except Exception as e:
                    print(f"❌ Google Vision API initialization failed: {e}")
                    self.client = None
                    
        except Exception as e:
            print(f"❌ Google Vision API initialization failed: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Google Vision APIが利用可能かどうかを確認"""
        return self.client is not None
    
    async def extract_text(self, image_path: str, session_id: str = None) -> OCRResult:
        """Google Vision APIを使って画像からテキストを抽出"""
        print("🔍 Starting OCR with Google Vision API...")
        
        # Vision API利用可能性チェック
        if not self.is_available():
            from app.services.auth.unified_auth import get_auth_troubleshooting
            return self._create_error_result(
                "Google Vision APIが利用できません。認証情報を確認してください。",
                error_type="api_unavailable",
                suggestions=get_auth_troubleshooting()
            )
        
        try:
            # 画像ファイル検証
            self.validate_image_file(image_path)
            
            # 画像ファイル読み込み
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Vision API呼び出し
            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)
            
            # エラーレスポンスチェック
            if response.error.message:
                raise Exception(f'Vision API Error: {response.error.message}')
            
            # テキスト抽出
            texts = response.text_annotations
            extracted_text = texts[0].description if texts else ""
            
            print(f"✅ Google Vision OCR Complete: Extracted {len(extracted_text)} characters")
            
            # 結果が空の場合の処理
            if not extracted_text.strip():
                return self._create_error_result(
                    "画像からテキストを検出できませんでした。より鮮明な画像をお試しください。",
                    error_type="no_text_detected",
                    suggestions=[
                        "より鮮明な画像を使用してください",
                        "文字が大きく写っている画像を選んでください",
                        "照明が良い環境で撮影した画像を使用してください",
                        "メニューテキストが中央に写っている画像を選んでください"
                    ]
                )
            
            # 成功結果
            return self._create_success_result(
                extracted_text,
                metadata={
                    "total_detections": len(texts),
                    "file_size": len(content),
                    "text_length": len(extracted_text),
                    "stage": 1
                }
            )
                
        except FileNotFoundError as e:
            return self._create_error_result(
                str(e),
                error_type="file_not_found"
            )
        
        except ValueError as e:
            return self._create_error_result(
                str(e),
                error_type="validation_error"
            )
            
        except Exception as e:
            print(f"❌ Google Vision OCR Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            error_str = str(e).lower()
            if "permission" in error_str or "forbidden" in error_str:
                error_type = "permission_error"
                suggestions = [
                    "Google Cloud認証が正しく設定されているか確認してください",
                    "サービスアカウントにVision API権限があるか確認してください"
                ]
            elif "quota" in error_str or "limit" in error_str:
                error_type = "quota_exceeded"
                suggestions = [
                    "Vision APIクォータを確認してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            elif "network" in error_str or "connection" in error_str:
                error_type = "network_error"
                suggestions = [
                    "インターネット接続を確認してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            else:
                suggestions = [
                    "画像ファイルが破損していないか確認してください",
                    "サポートされている画像形式（JPG、PNG、GIF）を使用してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            
            return self._create_error_result(
                f"OCR処理中にエラーが発生しました: {str(e)}",
                error_type=error_type,
                suggestions=suggestions
            )
