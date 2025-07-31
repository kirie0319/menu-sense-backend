from pydantic import BaseModel
from typing import List

class CORSSettings(BaseModel):
    """CORS設定クラス"""
    origins: List[str] = [
        "http://localhost:3000",
        "https://menu-sense-frontend.vercel.app",
        "https://app.yuyadevs.org",
    ]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]
    expose_headers: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
    
    def get_cors_config(self) -> dict:
        """CORS設定辞書を取得"""
        return {
            "allow_origins": self.origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "expose_headers": self.expose_headers
        }
    
    def is_origin_allowed(self, origin: str) -> bool:
        """指定されたoriginが許可されているかチェック"""
        if "*" in self.origins:
            return True
        
        # 完全一致チェック
        if origin in self.origins:
            return True
        
        # ワイルドカードパターンチェック
        for allowed_origin in self.origins:
            if "*" in allowed_origin:
                pattern = allowed_origin.replace("*", "")
                if pattern in origin:
                    return True
        
        return False


# グローバルインスタンス
cors_settings = CORSSettings()

def get_cors_settings():
    return cors_settings