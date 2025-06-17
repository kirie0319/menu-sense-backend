#!/usr/bin/env python3
"""
Menu Sensor Backend Test Runner

テストを実行するためのスクリプト
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command: list, description: str = "") -> int:
    """コマンドを実行し、結果を返す"""
    if description:
        print(f"🔄 {description}")
    
    print(f"💻 実行中: {' '.join(command)}")
    result = subprocess.run(command, capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {description} 完了")
    else:
        print(f"❌ {description} 失敗 (exit code: {result.returncode})")
    
    return result.returncode


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="Menu Sensor Backend テストランナー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_tests.py                    # 全テスト実行
  python run_tests.py --unit             # ユニットテストのみ
  python run_tests.py --integration      # 統合テストのみ
  python run_tests.py --api              # APIテストのみ
  python run_tests.py --coverage         # カバレッジ付きで実行
  python run_tests.py --fast             # 高速テスト（slowマークをスキップ）
  python run_tests.py --external         # 外部API依存テストを含む
  python run_tests.py --verbose          # 詳細出力
        """
    )
    
    # テストタイプの選択
    parser.add_argument("--unit", action="store_true", help="ユニットテストのみ実行")
    parser.add_argument("--integration", action="store_true", help="統合テストのみ実行")
    parser.add_argument("--api", action="store_true", help="APIテストのみ実行")
    
    # テスト実行オプション
    parser.add_argument("--coverage", action="store_true", help="カバレッジ測定付きで実行")
    parser.add_argument("--fast", action="store_true", help="高速テスト（slowマークをスキップ）")
    parser.add_argument("--external", action="store_true", help="外部API依存テストを含む")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")
    parser.add_argument("--parallel", "-n", type=int, default=1, help="並列実行数")
    
    # 特定のテストファイルやテスト関数
    parser.add_argument("--file", type=str, help="特定のテストファイルを実行")
    parser.add_argument("--test", type=str, help="特定のテスト関数を実行")
    
    # その他のオプション
    parser.add_argument("--install-deps", action="store_true", help="テスト依存関係をインストール")
    parser.add_argument("--lint", action="store_true", help="リント検査も実行")
    
    args = parser.parse_args()
    
    # 依存関係のインストール
    if args.install_deps:
        print("📦 テスト依存関係をインストール中...")
        result = run_command([
            sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
        ], "テスト依存関係のインストール")
        if result != 0:
            return result
    
    # リント検査
    if args.lint:
        print("🔍 リント検査を実行中...")
        try:
            # flake8でのリント検査
            run_command([
                sys.executable, "-m", "flake8", "app", "tests", "--max-line-length=100"
            ], "flake8 リント検査")
        except FileNotFoundError:
            print("⚠️ flake8が見つかりません。スキップします。")
    
    # pytestコマンドの構築
    pytest_command = [sys.executable, "-m", "pytest"]
    
    # テストディレクトリの指定
    if args.unit:
        pytest_command.append("tests/unit")
    elif args.integration:
        pytest_command.append("tests/integration")
    elif args.api:
        pytest_command.append("tests/api")
    elif args.file:
        pytest_command.append(args.file)
    else:
        pytest_command.append("tests")
    
    # 特定のテスト関数
    if args.test:
        pytest_command.extend(["-k", args.test])
    
    # マーカーの設定
    markers = []
    if args.fast:
        markers.append("not slow")
    if not args.external:
        markers.append("not external")
    
    if markers:
        pytest_command.extend(["-m", " and ".join(markers)])
    
    # カバレッジオプション
    if args.coverage:
        pytest_command.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])
    
    # 詳細出力
    if args.verbose:
        pytest_command.append("-v")
    else:
        pytest_command.append("-q")
    
    # 並列実行
    if args.parallel > 1:
        pytest_command.extend(["-n", str(args.parallel)])
    
    # その他の有用なオプション
    pytest_command.extend([
        "--tb=short",  # トレースバックを短縮
        "--strict-markers",  # 未定義マーカーでエラー
        "--disable-warnings"  # 警告を無効化
    ])
    
    # テスト実行
    print("🧪 テストを実行中...")
    print("=" * 60)
    
    result = run_command(pytest_command, "テスト実行")
    
    if result == 0:
        print("\n" + "=" * 60)
        print("🎉 全てのテストが成功しました！")
        
        if args.coverage:
            print("📊 カバレッジレポートが htmlcov/ ディレクトリに生成されました")
    else:
        print("\n" + "=" * 60)
        print("💥 テストが失敗しました。詳細を確認してください。")
    
    return result


if __name__ == "__main__":
    sys.exit(main()) 