-- メニュー翻訳システム用データベースセットアップ

-- ユーザー（ロール）の作成
CREATE USER menu_user WITH PASSWORD 'menu_password';

-- データベースの作成
CREATE DATABASE menu_translation_db OWNER menu_user;

-- 権限の付与
GRANT ALL PRIVILEGES ON DATABASE menu_translation_db TO menu_user;

-- 接続権限の付与
GRANT CONNECT ON DATABASE menu_translation_db TO menu_user;

-- スキーマ権限の付与（データベースに接続してから実行）
\c menu_translation_db
GRANT ALL ON SCHEMA public TO menu_user;
