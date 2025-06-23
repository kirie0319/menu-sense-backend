# 📐 統一認証システム ガイド

## 概要

Menu Sensor Backendの統一認証システムは、複数の認証方法を一元化し、一貫性のあるインターフェースでGoogle Cloud認証情報を管理します。

## 🎯 主要な特徴

- **複数認証方法の統一**: AWS Secrets Manager、環境変数、ファイルベースの認証を一つのインターフェースで管理
- **自動フォールバック**: 優先度に基づいて複数の認証方法を自動的に試行
- **詳細なトラブルシューティング**: 問題発生時に具体的な解決策を提供
- **完全な後方互換性**: 既存のコードに影響を与えずに統合
- **リアルタイム診断**: 認証状態と使用中の認証方法をリアルタイムで監視

## 🔧 アーキテクチャ

### 認証優先順位

1. **AWS Secrets Manager** （推奨 - 本番環境）
2. **環境変数JSON** （開発環境）
3. **ファイルパス** （ローカル開発）
4. **GOOGLE_APPLICATION_CREDENTIALS** （システム環境変数）

### コンポーネント構成

```
app/services/auth/
├── unified_auth.py          # 統一認証システムの主要実装
├── credentials.py           # 後方互換性ラッパー
├── clients.py              # APIクライアント管理
├── aws_secrets.py          # AWS Secrets Manager統合
└── __init__.py             # 統合インターフェース
```

## 🚀 使用方法

### 1. 基本的な使用

```python
from app.services.auth.unified_auth import get_unified_auth_manager

# 統一認証マネージャーを取得
auth_manager = get_unified_auth_manager()

# 認証情報を取得
credentials = auth_manager.get_credentials()

# 認証状態を確認
if auth_manager.is_available():
    print("認証情報が利用可能です")
```

### 2. 認証状態の詳細確認

```python
from app.services.auth.unified_auth import get_auth_status

auth_status = get_auth_status()
print(f"認証方法: {auth_status['method']}")
print(f"認証ソース: {auth_status['source']}")
print(f"利用可能: {auth_status['available']}")
```

### 3. トラブルシューティング情報の取得

```python
from app.services.auth.unified_auth import get_auth_troubleshooting

if not auth_manager.is_available():
    suggestions = get_auth_troubleshooting()
    for suggestion in suggestions:
        print(f"💡 {suggestion}")
```

### 4. 後方互換性インターフェース

```python
# 既存のコードはそのまま動作
from app.services.auth import get_google_credentials

credentials = get_google_credentials()
```

## ⚙️ 設定方法

### Option 1: AWS Secrets Manager（推奨）

```bash
# 環境変数
USE_AWS_SECRETS_MANAGER=true
AWS_REGION=us-east-1
AWS_SECRET_NAME=prod/menu-sense/google-credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Google認証情報をAWSに保存
aws secretsmanager create-secret \
    --name "prod/menu-sense/google-credentials" \
    --description "Google Cloud credentials for Menu Sense" \
    --secret-string file://service-account-key.json
```

### Option 2: 環境変数JSON

```bash
USE_AWS_SECRETS_MANAGER=false
GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project",...}'
```

### Option 3: ファイルパス

```bash
USE_AWS_SECRETS_MANAGER=false
GOOGLE_CREDENTIALS_JSON=/path/to/service-account-key.json
```

### Option 4: Google Application Credentials

```bash
USE_AWS_SECRETS_MANAGER=false
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## 🔍 診断とテスト

### 1. 統一認証システムのテスト

```bash
python test_unified_auth.py
```

このテストスクリプトは以下を確認します：
- 環境変数の設定状況
- 認証情報の読み込み状況
- APIクライアントの初期化状況
- 後方互換性の動作

### 2. セットアップ確認

```bash
python check_setup.py
```

### 3. APIエンドポイントでの診断

```bash
curl http://localhost:8000/api/v1/diagnostic | jq
```

## 🛠️ プロダクション環境での運用

### Railway/Herokuでの設定

```bash
# 環境変数として設定
USE_AWS_SECRETS_MANAGER=true
AWS_REGION=us-east-1
AWS_SECRET_NAME=prod/menu-sense/google-credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### AWS ECS/EC2での設定

```bash
# IAM Role使用時（推奨）
USE_AWS_SECRETS_MANAGER=true
AWS_REGION=us-east-1
AWS_SECRET_NAME=prod/menu-sense/google-credentials
# AWS認証情報は自動取得（IAM Role）
```

### セキュリティのベストプラクティス

1. **最小権限原則**: IAMユーザーには`secretsmanager:GetSecretValue`権限のみ付与
2. **認証情報のローテーション**: 定期的にAWS認証情報を更新
3. **IAM Role使用**: 可能な限りIAM Roleを使用（EC2/ECS/Lambda等）
4. **監査ログ**: CloudTrailで認証情報アクセスを監視

## 📊 認証方法の比較

| 認証方法 | セキュリティ | 管理容易性 | 本番適用 | 推奨度 |
|---------|-------------|-----------|---------|--------|
| AWS Secrets Manager | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **最推奨** |
| 環境変数JSON | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 開発環境 |
| ファイルパス | ⭐⭐ | ⭐⭐ | ⭐ | ローカル開発 |
| Google App Creds | ⭐⭐ | ⭐⭐ | ⭐⭐ | システム環境 |

## 🔧 トラブルシューティング

### 一般的な問題と解決策

#### 1. 認証情報が見つからない

**症状**: `❌ No valid Google Cloud credentials found`

**解決策**:
1. 環境変数の設定を確認: `echo $USE_AWS_SECRETS_MANAGER`
2. AWS認証情報の設定を確認: `aws sts get-caller-identity`
3. Google認証情報の形式を確認: `python test_unified_auth.py`

#### 2. AWS Secrets Manager接続エラー

**症状**: `❌ AWS Secrets Manager connection failed`

**解決策**:
1. AWS認証情報を確認: `aws configure list`
2. IAM権限を確認: `secretsmanager:GetSecretValue`
3. ネットワーク接続を確認

#### 3. Google API初期化エラー

**症状**: `❌ Google Vision API initialization failed`

**解決策**:
1. 認証情報の形式を確認
2. Google Cloud APIの有効化を確認
3. サービスアカウントの権限を確認

### デバッグのヒント

1. **詳細ログの有効化**: 統一認証システムは詳細なログを出力
2. **段階的テスト**: 各認証方法を個別にテスト
3. **診断エンドポイント**: `/api/v1/diagnostic`で詳細情報を確認

## 🔄 マイグレーション

### 既存システムからの移行

1. **既存コードは変更不要**: 後方互換性により既存のインターフェースがそのまま使用可能
2. **段階的移行**: 開発環境で確認後、本番環境に適用
3. **ロールバック対応**: 従来の認証方法もサポートしているため安全

### 移行チェックリスト

- [ ] 統一認証システムのテスト実行
- [ ] 環境変数の設定確認
- [ ] AWS Secrets Managerの設定（本番環境）
- [ ] APIクライアントの動作確認
- [ ] 診断エンドポイントでの最終確認

## 🎯 今後の拡張

- **Azure Key Vault サポート**: Azure環境での秘密情報管理
- **HashiCorp Vault サポート**: エンタープライズ環境での統合
- **認証情報の自動ローテーション**: より高度なセキュリティ機能
- **詳細監査ログ**: 認証情報アクセスの詳細トラッキング

---

このガイドにより、統一認証システムを安全かつ効率的に運用できます。問題が発生した場合は、まず`python test_unified_auth.py`を実行して問題を特定してください。 