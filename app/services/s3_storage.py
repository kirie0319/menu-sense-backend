"""
S3ストレージサービス
画像生成後にAWS S3にアップロードする機能を提供
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, BinaryIO
import os
import logging
from datetime import datetime
from PIL import Image
from io import BytesIO

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """AWS S3への画像アップロードサービス"""
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.image_prefix = settings.S3_IMAGE_PREFIX
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """S3クライアントを初期化"""
        try:
            if settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY:
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY
                )
            else:
                # IAMロールまたはAWS CLI設定を使用
                self.s3_client = boto3.client('s3', region_name=self.region)
            
            logger.info(f"✅ S3 client initialized for bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def is_available(self) -> bool:
        """S3サービスが利用可能かチェック"""
        if not settings.USE_S3_STORAGE:
            return False
        
        if not self.s3_client:
            return False
        
        try:
            # バケットの存在確認
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            logger.error(f"❌ S3 bucket access error: {e}")
            return False
        except NoCredentialsError:
            logger.error("❌ S3 credentials not available")
            return False
    
    def upload_image(
        self, 
        image_data: bytes, 
        filename: str, 
        content_type: str = "image/jpeg",
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        画像をS3にアップロード
        
        Args:
            image_data: 画像のバイナリデータ
            filename: ファイル名
            content_type: コンテンツタイプ
            metadata: 追加メタデータ
            
        Returns:
            S3のパブリックURL（成功時）またはNone（失敗時）
        """
        if not self.is_available():
            logger.error("❌ S3 service not available")
            return None
        
        try:
            # S3キーを生成（プレフィックス付き）
            timestamp = datetime.now().strftime("%Y/%m/%d")
            s3_key = f"{self.image_prefix}/{timestamp}/{filename}"
            
            # メタデータを準備（ASCII文字のみ許可されるため変換）
            upload_metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'service': 'menu-sense-image-generator'
            }
            
            # メタデータがある場合、ASCII安全な形式に変換
            if metadata:
                safe_metadata = self._sanitize_metadata(metadata)
                upload_metadata.update(safe_metadata)
            
            # S3にアップロード（ACLは使用せず、バケットポリシーに依存）
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
                Metadata=upload_metadata
            )
            
            # パブリックURLを生成
            public_url = settings.S3_PUBLIC_URL_TEMPLATE.format(
                bucket=self.bucket_name,
                region=self.region,
                key=s3_key
            )
            
            logger.info(f"✅ Image uploaded to S3: {s3_key}")
            return public_url
            
        except ClientError as e:
            logger.error(f"❌ S3 upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during S3 upload: {e}")
            return None
    
    def upload_pil_image(
        self, 
        pil_image: Image.Image, 
        filename: str,
        format: str = "JPEG",
        quality: int = 95,
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        PIL ImageオブジェクトをS3にアップロード
        
        Args:
            pil_image: PIL Imageオブジェクト
            filename: ファイル名
            format: 画像フォーマット（JPEG, PNG等）
            quality: JPEG品質（1-100）
            metadata: 追加メタデータ
            
        Returns:
            S3のパブリックURL（成功時）またはNone（失敗時）
        """
        try:
            # PIL Imageをバイナリデータにエンコード
            buffer = BytesIO()
            
            # RGB変換（JPEG保存時のエラーを防ぐため）
            if format.upper() == "JPEG" and pil_image.mode in ("RGBA", "P"):
                pil_image = pil_image.convert("RGB")
            
            # 画像を保存
            save_kwargs = {}
            if format.upper() == "JPEG":
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            
            pil_image.save(buffer, format=format, **save_kwargs)
            image_data = buffer.getvalue()
            
            # コンテンツタイプを決定
            content_type_map = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp"
            }
            content_type = content_type_map.get(format.upper(), "image/jpeg")
            
            # S3にアップロード
            return self.upload_image(image_data, filename, content_type, metadata)
            
        except Exception as e:
            logger.error(f"❌ Error converting PIL image for S3 upload: {e}")
            return None
    
    def delete_image(self, s3_key: str) -> bool:
        """
        S3から画像を削除
        
        Args:
            s3_key: S3キー
            
        Returns:
            削除成功フラグ
        """
        if not self.is_available():
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"✅ Image deleted from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 delete error: {e}")
            return False
    
    def list_images(self, prefix: Optional[str] = None, max_keys: int = 1000) -> list:
        """
        S3バケットから画像ファイルのリストを取得
        
        Args:
            prefix: フィルタリング用のプレフィックス（例: "generated-images/2024/01/01"）
            max_keys: 最大取得件数
            
        Returns:
            画像ファイル情報のリスト
        """
        if not self.is_available():
            logger.error("❌ S3 service not available")
            return []
        
        try:
            # プレフィックスを設定（デフォルトは image_prefix）
            search_prefix = prefix if prefix else self.image_prefix
            
            # S3からオブジェクトリストを取得
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=search_prefix,
                MaxKeys=max_keys
            )
            
            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # 画像ファイルのみフィルタリング
                    if self._is_image_file(obj['Key']):
                        # パブリックURLを生成
                        public_url = settings.S3_PUBLIC_URL_TEMPLATE.format(
                            bucket=self.bucket_name,
                            region=self.region,
                            key=obj['Key']
                        )
                        
                        images.append({
                            'key': obj['Key'],
                            'url': public_url,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'filename': obj['Key'].split('/')[-1],  # ファイル名のみ
                            'date_path': '/'.join(obj['Key'].split('/')[1:-1])  # 日付パス部分
                        })
            
            logger.info(f"✅ Found {len(images)} images in S3 bucket")
            return images
            
        except ClientError as e:
            logger.error(f"❌ S3 list error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error listing S3 images: {e}")
            return []
    
    def get_image_by_key(self, s3_key: str) -> Optional[dict]:
        """
        S3キーから画像情報を取得
        
        Args:
            s3_key: S3キー
            
        Returns:
            画像情報辞書またはNone
        """
        if not self.is_available():
            return None
        
        try:
            # オブジェクトのメタデータを取得
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            # パブリックURLを生成
            public_url = settings.S3_PUBLIC_URL_TEMPLATE.format(
                bucket=self.bucket_name,
                region=self.region,
                key=s3_key
            )
            
            return {
                'key': s3_key,
                'url': public_url,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response['ContentType'],
                'metadata': response.get('Metadata', {}),
                'filename': s3_key.split('/')[-1],
                'date_path': '/'.join(s3_key.split('/')[1:-1])
            }
            
        except ClientError as e:
            logger.error(f"❌ S3 get image error: {e}")
            return None
    
    def list_images_by_date(self, date_str: str) -> list:
        """
        指定日付の画像を取得
        
        Args:
            date_str: 日付文字列（YYYY/MM/DD または YYYY-MM-DD）
            
        Returns:
            画像ファイル情報のリスト
        """
        # 日付フォーマットを統一
        formatted_date = date_str.replace('-', '/')
        prefix = f"{self.image_prefix}/{formatted_date}"
        
        return self.list_images(prefix=prefix)
    
    def search_images_by_filename(self, filename_pattern: str) -> list:
        """
        ファイル名パターンで画像を検索
        
        Args:
            filename_pattern: ファイル名パターン（部分一致）
            
        Returns:
            マッチした画像ファイル情報のリスト
        """
        all_images = self.list_images()
        
        # ファイル名でフィルタリング
        matching_images = []
        for image in all_images:
            if filename_pattern.lower() in image['filename'].lower():
                matching_images.append(image)
        
        return matching_images
    
    def get_recent_images(self, limit: int = 50) -> list:
        """
        最新の画像を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            最新の画像ファイル情報のリスト（最新順）
        """
        images = self.list_images(max_keys=limit * 2)  # 余裕を持って取得
        
        # 最終更新日時でソート（最新順）
        images.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return images[:limit]
    
    def _is_image_file(self, key: str) -> bool:
        """
        ファイルが画像かどうかを判定
        
        Args:
            key: S3キー
            
        Returns:
            画像ファイルかどうか
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        return any(key.lower().endswith(ext) for ext in image_extensions)
    
    def _sanitize_metadata(self, metadata: dict) -> dict:
        """
        メタデータをS3で許可されるASCII文字のみに変換
        
        Args:
            metadata: 元のメタデータ辞書
            
        Returns:
            ASCII安全なメタデータ辞書
        """
        import base64
        import json
        
        safe_metadata = {}
        
        for key, value in metadata.items():
            # キーはASCII文字のみに制限
            safe_key = key.encode('ascii', 'ignore').decode('ascii')
            if not safe_key:
                continue
                
            # 値を処理
            if isinstance(value, str):
                try:
                    # ASCII文字かチェック
                    value.encode('ascii')
                    safe_metadata[safe_key] = value
                except UnicodeEncodeError:
                    # Unicode文字が含まれる場合はBase64エンコード
                    encoded_value = base64.b64encode(value.encode('utf-8')).decode('ascii')
                    safe_metadata[f"{safe_key}_b64"] = encoded_value
                    safe_metadata[f"{safe_key}_encoding"] = "base64_utf8"
            else:
                # 文字列以外はJSON文字列として保存
                json_str = json.dumps(value, ensure_ascii=True)
                safe_metadata[safe_key] = json_str
        
        return safe_metadata
    
    def get_bucket_info(self) -> dict:
        """バケット情報を取得"""
        return {
            "bucket_name": self.bucket_name,
            "region": self.region,
            "image_prefix": self.image_prefix,
            "available": self.is_available(),
            "use_s3_storage": settings.USE_S3_STORAGE
        }


# グローバルインスタンス
s3_storage = S3StorageService() 