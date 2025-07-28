"""
OCR Test Suite - 包括的テストランナー
OCRService, GoogleVisionClient, および統合テストを管理

このファイルは以下のテストを統合管理します：
- OCRService 単体テスト
- GoogleVisionClient 単体テスト  
- OCRService 統合テスト
- GoogleVisionClient 統合テスト
- エラーハンドリングテスト
"""
import pytest
import sys
import subprocess
from pathlib import Path
from typing import Dict, List
import asyncio

# テスト設定
PYTEST_ARGS = ["-v", "-s", "--tb=short"]


class OCRTestSuite:
    """OCR関連テストの包括的管理クラス"""
    
    def __init__(self):
        self.test_results: Dict[str, bool] = {}
        self.current_dir = Path(__file__).parent
        
    def run_unit_tests(self) -> bool:
        """全ての単体テストを実行"""
        print("🔬 OCR Unit Tests - 単体テスト実行中...")
        print("=" * 60)
        
        test_commands = [
            # OCRService 単体テスト
            {
                "name": "OCRService Unit Tests",
                "cmd": [
                    sys.executable, "-m", "pytest",
                    "tests/services/test_ocr_service.py::TestOCRService",
                    "tests/services/test_ocr_service.py::TestOCRServiceFactory", 
                    "tests/services/test_ocr_service.py::TestOCRServiceErrorHandling"
                ] + PYTEST_ARGS
            },
            # GoogleVisionClient 単体テスト
            {
                "name": "GoogleVisionClient Unit Tests", 
                "cmd": [
                    sys.executable, "-m", "pytest",
                    "tests/services/test_google_vision_client.py::TestGoogleVisionClient",
                    "tests/services/test_google_vision_client.py::TestGoogleVisionClientFactory"
                ] + PYTEST_ARGS
            }
        ]
        
        all_passed = True
        for test_config in test_commands:
            print(f"\n📋 実行中: {test_config['name']}")
            print("-" * 40)
            
            result = subprocess.run(test_config["cmd"], capture_output=True, text=True)
            
            passed = result.returncode == 0
            self.test_results[test_config["name"]] = passed
            all_passed = all_passed and passed
            
            if passed:
                print(f"✅ {test_config['name']}: PASSED")
            else:
                print(f"❌ {test_config['name']}: FAILED")
                print("STDOUT:", result.stdout[-500:])  # 最後の500文字のみ表示
                if result.stderr:
                    print("STDERR:", result.stderr[-300:])
        
        return all_passed

    def run_integration_tests(self) -> bool:
        """全ての統合テストを実行"""
        print("\n🔗 OCR Integration Tests - 統合テスト実行中...")
        print("=" * 60)
        
        test_commands = [
            # OCRService 統合テスト
            {
                "name": "OCRService Integration Tests",
                "cmd": [
                    sys.executable, "-m", "pytest",
                    "tests/services/test_ocr_service.py::TestOCRServiceIntegration"
                ] + PYTEST_ARGS
            },
            # GoogleVisionClient 統合テスト
            {
                "name": "GoogleVisionClient Integration Tests",
                "cmd": [
                    sys.executable, "-m", "pytest", 
                    "tests/services/test_google_vision_client.py::TestGoogleVisionClientIntegration"
                ] + PYTEST_ARGS
            }
        ]
        
        all_passed = True
        for test_config in test_commands:
            print(f"\n📋 実行中: {test_config['name']}")
            print("-" * 40)
            
            result = subprocess.run(test_config["cmd"], capture_output=True, text=True)
            
            passed = result.returncode == 0
            self.test_results[test_config["name"]] = passed
            all_passed = all_passed and passed
            
            if passed:
                print(f"✅ {test_config['name']}: PASSED")
            else:
                print(f"❌ {test_config['name']}: FAILED")
                print("STDOUT:", result.stdout[-500:])
                if result.stderr:
                    print("STDERR:", result.stderr[-300:])
        
        return all_passed

    def run_specific_test_category(self, category: str) -> bool:
        """特定のカテゴリーのテストを実行"""
        category_commands = {
            "ocr_service": [
                sys.executable, "-m", "pytest",
                "tests/services/test_ocr_service.py",
                "-v", "-s"
            ],
            "google_vision": [
                sys.executable, "-m", "pytest", 
                "tests/services/test_google_vision_client.py",
                "-v", "-s"
            ],
            "unit_only": [
                sys.executable, "-m", "pytest",
                "tests/services/test_ocr_service.py::TestOCRService",
                "tests/services/test_ocr_service.py::TestOCRServiceFactory",
                "tests/services/test_ocr_service.py::TestOCRServiceErrorHandling",
                "tests/services/test_google_vision_client.py::TestGoogleVisionClient",
                "tests/services/test_google_vision_client.py::TestGoogleVisionClientFactory",
                "-v", "-s"
            ],
            "integration_only": [
                sys.executable, "-m", "pytest",
                "tests/services/test_ocr_service.py::TestOCRServiceIntegration", 
                "tests/services/test_google_vision_client.py::TestGoogleVisionClientIntegration",
                "-v", "-s"
            ]
        }
        
        if category not in category_commands:
            print(f"❌ 不明なカテゴリー: {category}")
            print(f"利用可能なカテゴリー: {list(category_commands.keys())}")
            return False
            
        print(f"\n🎯 {category} テスト実行中...")
        print("=" * 60)
        
        result = subprocess.run(category_commands[category], capture_output=True, text=True)
        passed = result.returncode == 0
        
        if passed:
            print(f"✅ {category}: PASSED")
        else:
            print(f"❌ {category}: FAILED")
            print("STDOUT:", result.stdout[-500:])
            if result.stderr:
                print("STDERR:", result.stderr[-300:])
        
        return passed

    def run_all_tests(self) -> bool:
        """全てのOCRテストを実行"""
        print("🚀 OCR Test Suite - 全テスト実行開始")
        print("=" * 80)
        
        # 単体テスト実行
        unit_passed = self.run_unit_tests()
        
        # 統合テスト実行
        integration_passed = self.run_integration_tests()
        
        # 結果サマリー
        self.print_test_summary()
        
        return unit_passed and integration_passed

    def print_test_summary(self):
        """テスト結果のサマリーを出力"""
        print("\n" + "=" * 80)
        print("📊 OCR Test Suite - 実行結果サマリー")
        print("=" * 80)
        
        passed_tests = [name for name, result in self.test_results.items() if result]
        failed_tests = [name for name, result in self.test_results.items() if not result]
        
        print(f"\n✅ 成功したテスト ({len(passed_tests)}):")
        for test_name in passed_tests:
            print(f"   - {test_name}")
        
        if failed_tests:
            print(f"\n❌ 失敗したテスト ({len(failed_tests)}):")
            for test_name in failed_tests:
                print(f"   - {test_name}")
        
        total_tests = len(self.test_results)
        success_rate = len(passed_tests) / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n📈 成功率: {success_rate:.1f}% ({len(passed_tests)}/{total_tests})")
        
        if success_rate == 100:
            print("🎉 全てのテストが成功しました！")
        elif success_rate >= 80:
            print("⚠️  一部のテストが失敗していますが、大部分は成功しています。")
        else:
            print("🚨 多くのテストが失敗しています。設定を確認してください。")

    def validate_test_environment(self) -> bool:
        """テスト環境の検証"""
        print("🔍 テスト環境検証中...")
        
        # 必要なファイルの存在確認
        required_files = [
            "tests/services/test_ocr_service.py",
            "tests/services/test_google_vision_client.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.current_dir.parent / file_path.replace("tests/services/", "")
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ 必要なテストファイルが見つかりません:")
            for file_path in missing_files:
                print(f"   - {file_path}")
            return False
        
        # テストデータディレクトリの確認
        test_data_dir = self.current_dir.parent / "data"
        if test_data_dir.exists():
            print(f"✅ テストデータディレクトリ存在: {test_data_dir}")
            
            # 画像ファイルの確認
            image_files = list(test_data_dir.glob("*.webp")) + list(test_data_dir.glob("*.jpg")) + list(test_data_dir.glob("*.png"))
            if image_files:
                print(f"📸 テスト画像ファイル ({len(image_files)}個):")
                for img_file in image_files[:3]:  # 最初の3つだけ表示
                    print(f"   - {img_file.name}")
                if len(image_files) > 3:
                    print(f"   - ... 他 {len(image_files) - 3} 個")
            else:
                print("⚠️  テスト画像ファイルが見つかりません（統合テストをスキップする可能性があります）")
        else:
            print("⚠️  テストデータディレクトリが見つかりません（統合テストをスキップする可能性があります）")
        
        print("✅ テスト環境検証完了")
        return True


# コマンドライン実行用の関数
def run_ocr_unit_tests():
    """OCR単体テストのみを実行"""
    suite = OCRTestSuite()
    return suite.run_unit_tests()


def run_ocr_integration_tests():
    """OCR統合テストのみを実行"""
    suite = OCRTestSuite()
    return suite.run_integration_tests()


def run_all_ocr_tests():
    """全OCRテストを実行"""
    suite = OCRTestSuite()
    suite.validate_test_environment()
    return suite.run_all_tests()


def run_ocr_tests_by_category(category: str):
    """カテゴリー別テスト実行"""
    suite = OCRTestSuite()
    return suite.run_specific_test_category(category)


# pytest マーク用の関数
@pytest.mark.ocr
@pytest.mark.unit
def test_run_ocr_unit_tests():
    """OCR単体テストをpytestから実行"""
    assert run_ocr_unit_tests()


@pytest.mark.ocr
@pytest.mark.integration
def test_run_ocr_integration_tests():
    """OCR統合テストをpytestから実行"""
    assert run_ocr_integration_tests()


@pytest.mark.ocr
def test_run_all_ocr_tests():
    """全OCRテストをpytestから実行"""
    assert run_all_ocr_tests()


if __name__ == "__main__":
    """
    コマンドライン実行時の引数処理
    
    使用例:
    python test_ocr_suite.py                    # 全テスト実行
    python test_ocr_suite.py unit              # 単体テストのみ
    python test_ocr_suite.py integration       # 統合テストのみ
    python test_ocr_suite.py ocr_service       # OCRServiceのみ
    python test_ocr_suite.py google_vision     # GoogleVisionClientのみ
    """
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        
        if category == "unit":
            success = run_ocr_unit_tests()
        elif category == "integration":
            success = run_ocr_integration_tests()
        elif category in ["ocr_service", "google_vision", "unit_only", "integration_only"]:
            success = run_ocr_tests_by_category(category)
        else:
            print(f"❌ 不明な引数: {category}")
            print("使用可能な引数: unit, integration, ocr_service, google_vision, unit_only, integration_only")
            sys.exit(1)
    else:
        # 引数なしの場合は全テスト実行
        success = run_all_ocr_tests()
    
    # 終了コード設定
    sys.exit(0 if success else 1) 