#!/usr/bin/env python3
"""
OCR精度テストスイート
OCRの精度を測定し、改善のための詳細な分析を行います
"""

import os
import sys
import asyncio
import time
import json
import statistics
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import mimetypes
from datetime import datetime

# プロジェクトのルートを追加
sys.path.append(os.path.dirname(__file__))

from app.services.ocr import extract_text, ocr_manager, OCRProvider
from app.services.ocr.base import OCRResult
from app.services.ocr.gemini import GeminiOCRService
from app.services.ocr.google_vision import GoogleVisionOCRService
from app.core.config import settings

class OCRTestMetrics:
    """OCRテスト結果の詳細な分析を行うクラス"""
    
    def __init__(self):
        self.test_results = []
        self.error_patterns = {}
        self.performance_metrics = {}
    
    def add_test_result(self, test_case: str, expected: str, actual: str, 
                       processing_time: float, service: str, metadata: dict = None):
        """テスト結果を追加"""
        result = {
            "test_case": test_case,
            "expected": expected,
            "actual": actual,
            "processing_time": processing_time,
            "service": service,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # 精度計算
        result.update(self._calculate_accuracy(expected, actual))
        self.test_results.append(result)
    
    def _calculate_accuracy(self, expected: str, actual: str) -> dict:
        """テキスト抽出精度の計算"""
        expected_chars = set(expected.lower().replace(" ", "").replace("\n", ""))
        actual_chars = set(actual.lower().replace(" ", "").replace("\n", ""))
        
        if not expected_chars:
            return {"character_accuracy": 0.0, "word_accuracy": 0.0, "similarity_score": 0.0}
        
        # 文字レベル精度
        common_chars = expected_chars.intersection(actual_chars)
        char_accuracy = len(common_chars) / len(expected_chars) if expected_chars else 0
        
        # 単語レベル精度
        expected_words = set(expected.lower().split())
        actual_words = set(actual.lower().split())
        common_words = expected_words.intersection(actual_words)
        word_accuracy = len(common_words) / len(expected_words) if expected_words else 0
        
        # 類似度スコア（レーベンシュタイン距離ベース）
        similarity_score = self._calculate_similarity(expected, actual)
        
        return {
            "character_accuracy": round(char_accuracy * 100, 2),
            "word_accuracy": round(word_accuracy * 100, 2),
            "similarity_score": round(similarity_score * 100, 2)
        }
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """レーベンシュタイン距離による類似度計算"""
        if len(s1) < len(s2):
            return self._calculate_similarity(s2, s1)
        
        if len(s2) == 0:
            return 0.0
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        max_len = max(len(s1), len(s2))
        return 1 - (previous_row[-1] / max_len) if max_len > 0 else 1.0
    
    def generate_report(self) -> dict:
        """詳細なテストレポートを生成"""
        if not self.test_results:
            return {"error": "テスト結果がありません"}
        
        # 基本統計
        char_accuracies = [r["character_accuracy"] for r in self.test_results]
        word_accuracies = [r["word_accuracy"] for r in self.test_results]
        similarities = [r["similarity_score"] for r in self.test_results]
        processing_times = [r["processing_time"] for r in self.test_results]
        
        # サービス別統計
        services = {}
        for result in self.test_results:
            service = result["service"]
            if service not in services:
                services[service] = []
            services[service].append(result)
        
        service_stats = {}
        for service, results in services.items():
            service_char_acc = [r["character_accuracy"] for r in results]
            service_word_acc = [r["word_accuracy"] for r in results]
            service_times = [r["processing_time"] for r in results]
            
            service_stats[service] = {
                "test_count": len(results),
                "average_character_accuracy": round(statistics.mean(service_char_acc), 2),
                "average_word_accuracy": round(statistics.mean(service_word_acc), 2),
                "average_processing_time": round(statistics.mean(service_times), 2),
                "accuracy_std": round(statistics.stdev(service_char_acc) if len(service_char_acc) > 1 else 0, 2)
            }
        
        return {
            "test_summary": {
                "total_tests": len(self.test_results),
                "test_timestamp": datetime.now().isoformat(),
                "average_character_accuracy": round(statistics.mean(char_accuracies), 2),
                "average_word_accuracy": round(statistics.mean(word_accuracies), 2),
                "average_similarity_score": round(statistics.mean(similarities), 2),
                "average_processing_time": round(statistics.mean(processing_times), 2),
                "accuracy_range": {
                    "min_accuracy": round(min(char_accuracies), 2),
                    "max_accuracy": round(max(char_accuracies), 2),
                    "std_deviation": round(statistics.stdev(char_accuracies) if len(char_accuracies) > 1 else 0, 2)
                }
            },
            "service_comparison": service_stats,
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """精度改善のための推奨事項を生成"""
        recommendations = []
        
        if not self.test_results:
            return ["テスト結果が不足しています"]
        
        avg_accuracy = statistics.mean([r["character_accuracy"] for r in self.test_results])
        
        if avg_accuracy < 50:
            recommendations.extend([
                "全体的な精度が低いです。画像の前処理やOCRパラメータの調整を検討してください",
                "より高解像度の画像を使用することをお勧めします",
                "画像のコントラストや明度の調整を試してください"
            ])
        elif avg_accuracy < 80:
            recommendations.extend([
                "精度は中程度です。特定の文字パターンの認識改善を検討してください",
                "メニュー画像に特化したプロンプトの最適化をお勧めします"
            ])
        else:
            recommendations.extend([
                "優秀な精度です。現在の設定を維持しつつ、エッジケースの改善に注力してください",
                "処理速度の最適化に注力できます"
            ])
        
        # 処理時間の分析
        avg_time = statistics.mean([r["processing_time"] for r in self.test_results])
        if avg_time > 10:
            recommendations.append("処理時間が長いです。パラレル処理や画像サイズの最適化を検討してください")
        
        return recommendations

class OCRTester:
    """OCRテストを実行するメインクラス"""
    
    def __init__(self):
        self.metrics = OCRTestMetrics()
        self.test_images_dir = "test_images"
        self.results_dir = "test_results"
        
        # ディレクトリ作成
        os.makedirs(self.test_images_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
    
    def create_sample_test_cases(self):
        """サンプルテストケースの説明を生成"""
        sample_info = {
            "test_images_needed": [
                {
                    "filename": "menu_simple.jpg",
                    "description": "シンプルなメニュー画像（少ない項目、明確な文字）",
                    "expected_content": "料理名と価格が明確に記載されたもの"
                },
                {
                    "filename": "menu_complex.jpg", 
                    "description": "複雑なメニュー画像（多数の項目、装飾的なフォント）",
                    "expected_content": "多くの料理名、価格、説明文が含まれるもの"
                },
                {
                    "filename": "menu_handwritten.jpg",
                    "description": "手書きのメニュー（手書き文字の認識テスト）",
                    "expected_content": "手書きの料理名や価格"
                },
                {
                    "filename": "menu_low_quality.jpg",
                    "description": "低品質画像（ノイズ、ぼやけ、低解像度）",
                    "expected_content": "読み取りにくい状況での性能測定"
                },
                {
                    "filename": "menu_multilingual.jpg",
                    "description": "多言語メニュー（日本語、英語、その他の言語）",
                    "expected_content": "複数言語が混在するメニュー"
                }
            ],
            "setup_instructions": [
                f"1. {self.test_images_dir}/ ディレクトリにテスト用画像を配置してください",
                "2. 各画像に対応する期待結果をexpected_results.jsonに記載してください",
                "3. python test_ocr_advanced.py --run-tests でテストを実行してください"
            ]
        }
        
        with open(f"{self.test_images_dir}/SETUP_GUIDE.json", "w", encoding="utf-8") as f:
            json.dump(sample_info, f, ensure_ascii=False, indent=2)
        
        print(f"📝 テストセットアップガイドを作成しました: {self.test_images_dir}/SETUP_GUIDE.json")
    
    def load_expected_results(self) -> dict:
        """期待結果を読み込み"""
        expected_file = f"{self.test_images_dir}/expected_results.json"
        if os.path.exists(expected_file):
            with open(expected_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def save_expected_results_template(self):
        """期待結果のテンプレートを作成"""
        template = {
            "example_menu.jpg": {
                "expected_text": "ここに期待されるテキストを記載してください",
                "description": "このテストケースの説明",
                "difficulty": "easy|medium|hard"
            }
        }
        
        expected_file = f"{self.test_images_dir}/expected_results.json"
        if not os.path.exists(expected_file):
            with open(expected_file, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"📝 期待結果テンプレートを作成しました: {expected_file}")
    
    async def test_single_image(self, image_path: str, expected_text: str = "", 
                               service_name: str = "gemini") -> dict:
        """単一画像のOCRテスト"""
        print(f"🔍 Testing: {image_path}")
        
        start_time = time.time()
        try:
            if service_name.lower() == "gemini":
                result = await extract_text(image_path)
            else:
                # 他のサービスのテスト実装
                result = await self._test_other_service(image_path, service_name)
            
            processing_time = time.time() - start_time
            
            if result.success:
                self.metrics.add_test_result(
                    test_case=os.path.basename(image_path),
                    expected=expected_text,
                    actual=result.extracted_text,
                    processing_time=processing_time,
                    service=service_name,
                    metadata=result.metadata
                )
                
                return {
                    "success": True,
                    "extracted_text": result.extracted_text,
                    "processing_time": processing_time,
                    "service": service_name,
                    "text_length": len(result.extracted_text)
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "processing_time": processing_time,
                    "service": service_name
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "service": service_name
            }
    
    async def _test_other_service(self, image_path: str, service_name: str) -> OCRResult:
        """他のOCRサービスのテスト（拡張可能）"""
        if service_name.lower() == "google_vision":
            service = GoogleVisionOCRService()
            return await service.extract_text(image_path)
        else:
            # デフォルトはGemini
            return await extract_text(image_path)
    
    async def run_comprehensive_tests(self):
        """包括的なOCRテストを実行"""
        print("🚀 OCR包括的テストを開始します...")
        print("=" * 60)
        
        # テスト画像の検索
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            image_files.extend(Path(self.test_images_dir).glob(ext))
        
        if not image_files:
            print(f"❌ テスト画像が見つかりません: {self.test_images_dir}/")
            print("📝 まずテスト画像を配置してください。")
            self.create_sample_test_cases()
            self.save_expected_results_template()
            return
        
        # 期待結果の読み込み
        expected_results = self.load_expected_results()
        
        print(f"🖼️ 発見されたテスト画像: {len(image_files)} 件")
        
        # 各画像をテスト
        for image_path in image_files:
            image_name = image_path.name
            expected_text = expected_results.get(image_name, {}).get("expected_text", "")
            
            print(f"\n📸 Testing: {image_name}")
            
            # Geminiでテスト
            result = await self.test_single_image(str(image_path), expected_text, "gemini")
            
            if result["success"]:
                print(f"✅ Gemini OCR: {result['text_length']} chars in {result['processing_time']:.2f}s")
            else:
                print(f"❌ Gemini OCR Failed: {result['error']}")
        
        # レポート生成
        await self.generate_test_report()
    
    async def generate_test_report(self):
        """テストレポートを生成し保存"""
        print("\n📊 テストレポートを生成中...")
        
        report = self.metrics.generate_report()
        
        # レポートファイルの保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.results_dir}/ocr_test_report_{timestamp}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # コンソール出力
        self._print_report_summary(report)
        
        print(f"\n💾 詳細レポートを保存しました: {report_file}")
    
    def _print_report_summary(self, report: dict):
        """レポート要約をコンソールに出力"""
        summary = report.get("test_summary", {})
        services = report.get("service_comparison", {})
        recommendations = report.get("recommendations", [])
        
        print("\n" + "="*60)
        print("📈 OCRテスト結果サマリー")
        print("="*60)
        
        print(f"🧪 総テスト数: {summary.get('total_tests', 0)}")
        print(f"📝 平均文字精度: {summary.get('average_character_accuracy', 0)}%")
        print(f"🔤 平均単語精度: {summary.get('average_word_accuracy', 0)}%")
        print(f"⏱️ 平均処理時間: {summary.get('average_processing_time', 0)}秒")
        
        accuracy_range = summary.get('accuracy_range', {})
        print(f"📊 精度範囲: {accuracy_range.get('min_accuracy', 0)}% - {accuracy_range.get('max_accuracy', 0)}%")
        
        print("\n🔧 サービス別パフォーマンス:")
        for service, stats in services.items():
            print(f"  {service}:")
            print(f"    - 平均精度: {stats.get('average_character_accuracy', 0)}%")
            print(f"    - 処理時間: {stats.get('average_processing_time', 0)}秒")
            print(f"    - テスト数: {stats.get('test_count', 0)}")
        
        print("\n💡 改善提案:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    
    async def quick_test(self, image_path: str):
        """クイックテスト（単一画像）"""
        if not os.path.exists(image_path):
            print(f"❌ 画像ファイルが見つかりません: {image_path}")
            return
        
        print(f"🔍 クイックテスト: {image_path}")
        print("-" * 40)
        
        result = await self.test_single_image(image_path, service_name="gemini")
        
        if result["success"]:
            print(f"✅ OCR成功!")
            print(f"📝 抽出文字数: {result['text_length']}")
            print(f"⏱️ 処理時間: {result['processing_time']:.2f}秒")
            print("\n📄 抽出されたテキスト:")
            print("-" * 20)
            print(result["extracted_text"])
            print("-" * 20)
        else:
            print(f"❌ OCR失敗: {result['error']}")

# テスト実行関数
async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCR精度テストスイート")
    parser.add_argument("--quick", type=str, help="単一画像のクイックテスト")
    parser.add_argument("--run-tests", action="store_true", help="包括的テストを実行")
    parser.add_argument("--setup", action="store_true", help="テストセットアップガイドを作成")
    
    args = parser.parse_args()
    
    tester = OCRTester()
    
    if args.setup:
        tester.create_sample_test_cases()
        tester.save_expected_results_template()
        print("✅ テストセットアップ完了")
    elif args.quick:
        await tester.quick_test(args.quick)
    elif args.run_tests:
        await tester.run_comprehensive_tests()
    else:
        # デフォルト: セットアップガイド表示
        print("🧪 OCR精度テストスイート")
        print("=" * 40)
        print("使用方法:")
        print("  python test_ocr_advanced.py --setup          # テストセットアップ")
        print("  python test_ocr_advanced.py --quick image.jpg # クイックテスト")
        print("  python test_ocr_advanced.py --run-tests      # 包括的テスト")
        print()
        print("まずは --setup でテスト環境をセットアップしてください。")

if __name__ == "__main__":
    asyncio.run(main()) 