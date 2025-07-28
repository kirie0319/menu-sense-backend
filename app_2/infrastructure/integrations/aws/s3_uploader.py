"""
S3 Uploader - Infrastructure Layer
File upload service using AWS S3
"""

from typing import Optional
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("s3_uploader")


class S3Uploader:
    """
    AWS S3 アップロードクライアント
    
    画像ファイルのストレージを担当
    """
    
    def __init__(self):
        """
        AWS S3 クライアントを初期化
        """
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.aws.aws_access_key_id,
            aws_secret_access_key=settings.aws.aws_secret_access_key,
            region_name=settings.aws.aws_region
        )
        self.bucket_name = settings.aws.s3_bucket_name

    async def upload_image(
        self, 
        image_data: bytes, 
        file_extension: str = "jpg",
        folder: str = "menu_images"
    ) -> str:
        """
        画像をS3にアップロード
        
        Args:
            image_data: 画像バイナリデータ
            file_extension: ファイル拡張子
            folder: S3内のフォルダ名
            
        Returns:
            str: アップロードされた画像のURL
        """
        try:
            # ユニークなファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_name = f"{folder}/{timestamp}_{unique_id}.{file_extension}"
            
            # S3にアップロード
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=image_data,
                ContentType=f"image/{file_extension}",
                ACL='public-read'  # 公開読み取り許可
            )
            
            # URL生成
            image_url = f"https://{self.bucket_name}.s3.{settings.aws.aws_region}.amazonaws.com/{file_name}"
            
            logger.info(f"Image uploaded to S3: {file_name}")
            return image_url
            
        except ClientError as e:
            logger.error(f"Failed to upload image to S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise

    async def delete_image(self, image_url: str) -> bool:
        """
        S3から画像を削除
        
        Args:
            image_url: 削除対象の画像URL
            
        Returns:
            bool: 削除が成功したか
        """
        try:
            # URLからキーを抽出
            key = image_url.split(f"{self.bucket_name}.s3.{settings.aws.aws_region}.amazonaws.com/")[-1]
            
            # S3から削除
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Image deleted from S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete image from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    async def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        プリサインドURLを生成
        
        Args:
            key: S3オブジェクトキー
            expiration: URL有効期限（秒）
            
        Returns:
            str: プリサインドURL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for: {key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise 


@lru_cache(maxsize=1)
def get_s3_uploader() -> S3Uploader:
    """
    S3Uploader のシングルトンインスタンスを取得
    
    Returns:
        S3Uploader: シングルトンインスタンス
    """
    return S3Uploader() 