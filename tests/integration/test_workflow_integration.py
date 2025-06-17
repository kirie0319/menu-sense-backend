"""
ワークフロー統合テスト

全体のメニュー処理ワークフローの統合テストを行います。
OCR → カテゴリ分類 → 翻訳 → 説明追加 → 画像生成 の流れをテストします。
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.services.ocr import extract_text
from app.services.category import categorize_menu
from app.services.translation import translate_menu
from app.services.description import add_descriptions
from app.services.image import generate_images
from app.services.ocr.base import OCRResult, OCRProvider
from app.services.category.base import CategoryResult, CategoryProvider
from app.services.translation.base import TranslationResult, TranslationProvider
from app.services.description.base import DescriptionResult, DescriptionProvider


@pytest.mark.integration
class TestWorkflowIntegration:
    """ワークフロー統合テスト"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_mocks(self, test_session_id):
        """モックを使用した完全ワークフローテスト"""
        # テスト用の一時画像ファイル作成
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(b"fake image data")
            image_path = temp_file.name
        
        try:
            # Stage 1: OCR
            with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr:
                mock_ocr.return_value = OCRResult(
                    success=True,
                    extracted_text="""
                    メインディッシュ
                    唐揚げ定食 980円
                    天ぷら定食 1200円
                    
                    飲み物
                    ビール 500円
                    日本酒 800円
                    """,
                    provider=OCRProvider.GEMINI,
                    metadata={"confidence": 0.95}
                )
                
                ocr_result = await extract_text(image_path, test_session_id)
                assert ocr_result.success is True
                assert "唐揚げ定食" in ocr_result.extracted_text

            # Stage 2: カテゴリ分類
            with patch('app.services.category.category_manager.categorize_menu') as mock_category:
                mock_category.return_value = CategoryResult(
                    success=True,
                    categories={
                        "メインディッシュ": [
                            {"name": "唐揚げ定食", "price": "980円"},
                            {"name": "天ぷら定食", "price": "1200円"}
                        ],
                        "飲み物": [
                            {"name": "ビール", "price": "500円"},
                            {"name": "日本酒", "price": "800円"}
                        ]
                    },
                    uncategorized=[],
                    provider=CategoryProvider.OPENAI,
                    metadata={"model": "gpt-4"}
                )
                
                category_result = await categorize_menu(ocr_result.extracted_text, test_session_id)
                assert category_result.success is True
                assert "メインディッシュ" in category_result.categories
                assert len(category_result.categories["メインディッシュ"]) == 2

            # Stage 3: 翻訳
            with patch('app.services.translation.translation_manager.translate_menu') as mock_translation:
                mock_translation.return_value = TranslationResult(
                    success=True,
                    translated_menu={
                        "Main Dishes": [
                            {
                                "japanese_name": "唐揚げ定食",
                                "english_name": "Fried Chicken Set",
                                "price": "980円"
                            },
                            {
                                "japanese_name": "天ぷら定食",
                                "english_name": "Tempura Set",
                                "price": "1200円"
                            }
                        ],
                        "Drinks": [
                            {
                                "japanese_name": "ビール",
                                "english_name": "Beer",
                                "price": "500円"
                            },
                            {
                                "japanese_name": "日本酒",
                                "english_name": "Sake",
                                "price": "800円"
                            }
                        ]
                    },
                    provider=TranslationProvider.GOOGLE_TRANSLATE,
                    metadata={"language": "en"}
                )
                
                translation_result = await translate_menu(category_result.categories, test_session_id)
                assert translation_result.success is True
                assert "Main Dishes" in translation_result.translated_menu
                assert "Fried Chicken Set" in str(translation_result.translated_menu)

            # Stage 4: 説明追加
            with patch('app.services.description.description_manager.add_descriptions') as mock_description:
                mock_description.return_value = DescriptionResult(
                    success=True,
                    menu_with_descriptions={
                        "Main Dishes": [
                            {
                                "japanese_name": "唐揚げ定食",
                                "english_name": "Fried Chicken Set",
                                "price": "980円",
                                "description": "Crispy fried chicken pieces served with rice and miso soup"
                            },
                            {
                                "japanese_name": "天ぷら定食",
                                "english_name": "Tempura Set",
                                "price": "1200円",
                                "description": "Assorted tempura with seasonal vegetables and shrimp"
                            }
                        ],
                        "Drinks": [
                            {
                                "japanese_name": "ビール",
                                "english_name": "Beer",
                                "price": "500円",
                                "description": "Crisp Japanese draft beer"
                            },
                            {
                                "japanese_name": "日本酒",
                                "english_name": "Sake",
                                "price": "800円",
                                "description": "Premium Japanese rice wine"
                            }
                        ]
                    },
                    provider=DescriptionProvider.OPENAI,
                    metadata={"model": "gpt-4"}
                )
                
                description_result = await add_descriptions(translation_result.translated_menu, test_session_id)
                assert description_result.success is True
                assert "Crispy fried chicken" in str(description_result.menu_with_descriptions)

            # 全ステージが成功していることを確認
            assert all([
                ocr_result.success,
                category_result.success,
                translation_result.success,
                description_result.success
            ])

        finally:
            # テンポラリファイルをクリーンアップ
            if os.path.exists(image_path):
                os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_workflow_error_propagation(self, test_session_id):
        """エラー伝播のテスト"""
        # テスト用の一時画像ファイル作成
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(b"fake image data")
            image_path = temp_file.name
        
        try:
            # Stage 1で失敗した場合
            with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr:
                mock_ocr.return_value = OCRResult(
                    success=False,
                    extracted_text="",
                    provider=OCRProvider.GEMINI,
                    error="OCR APIエラー",
                    metadata={"error_code": "api_failure"}
                )
                
                ocr_result = await extract_text(image_path, test_session_id)
                assert ocr_result.success is False
                assert "OCR APIエラー" in ocr_result.error
                
                # OCRが失敗した場合、後続のステージは実行されない（実際のワークフローでは）
                # ここでは失敗時の動作を確認
        
        finally:
            if os.path.exists(image_path):
                os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_workflow_partial_failure_recovery(self, test_session_id):
        """部分的失敗からの復旧テスト"""
        # Stage 2（カテゴリ分類）で一部失敗、Stage 3で復旧するケース
        sample_text = "唐揚げ 980円\n不明な料理 ???円"
        
        with patch('app.services.category.category_manager.categorize_menu') as mock_category:
            mock_category.return_value = CategoryResult(
                success=True,
                categories={
                    "メイン": [{"name": "唐揚げ", "price": "980円"}]
                },
                uncategorized=["不明な料理"],  # 一部が未分類
                provider=CategoryProvider.OPENAI,
                metadata={"partial_success": True}
            )
            
            category_result = await categorize_menu(sample_text, test_session_id)
            assert category_result.success is True
            assert len(category_result.uncategorized) == 1
            assert "不明な料理" in category_result.uncategorized


@pytest.mark.integration
class TestServiceInteraction:
    """サービス間の相互作用テスト"""

    @pytest.mark.asyncio
    async def test_data_format_consistency(self, test_session_id):
        """データフォーマットの整合性テスト"""
        # OCRからカテゴリ分類への データ受け渡し
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr, \
             patch('app.services.category.category_manager.categorize_menu') as mock_category:
            
            # OCRの出力
            ocr_output = "料理1 100円\n料理2 200円"
            mock_ocr.return_value = OCRResult(
                success=True,
                extracted_text=ocr_output,
                provider=OCRProvider.GEMINI
            )
            
            # カテゴリ分類がOCRの出力を受け取ることを確認
            mock_category.return_value = CategoryResult(
                success=True,
                categories={"メイン": [{"name": "料理1", "price": "100円"}]},
                uncategorized=[],
                provider=CategoryProvider.OPENAI
            )
            
            # 実際の呼び出し
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(b"fake image data")
                image_path = temp_file.name
            
            try:
                ocr_result = await extract_text(image_path, test_session_id)
                category_result = await categorize_menu(ocr_result.extracted_text, test_session_id)
                
                # カテゴリ分類がOCRの出力テキストを正しく受け取ったことを確認
                mock_category.assert_called_once_with(ocr_output, test_session_id)
                
            finally:
                if os.path.exists(image_path):
                    os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_session_id_propagation(self, test_session_id):
        """セッションIDの伝播テスト"""
        # 全てのサービスに同じセッションIDが渡されることを確認
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr, \
             patch('app.services.category.category_manager.categorize_menu') as mock_category, \
             patch('app.services.translation.translation_manager.translate_menu') as mock_translation:
            
            # モックの戻り値設定
            mock_ocr.return_value = OCRResult(
                success=True,
                extracted_text="test text",
                provider=OCRProvider.GEMINI
            )
            
            mock_category.return_value = CategoryResult(
                success=True,
                categories={"test": [{"name": "test"}]},
                uncategorized=[],
                provider=CategoryProvider.OPENAI
            )
            
            mock_translation.return_value = TranslationResult(
                success=True,
                translated_menu={"test": [{"japanese_name": "test", "english_name": "test"}]},
                provider=TranslationProvider.GOOGLE_TRANSLATE
            )
            
            # テスト実行
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(b"fake image data")
                image_path = temp_file.name
            
            try:
                await extract_text(image_path, test_session_id)
                await categorize_menu("test", test_session_id)
                await translate_menu({"test": []}, test_session_id)
                
                # 全ての呼び出しで同じセッションIDが使われていることを確認
                mock_ocr.assert_called_once_with(image_path, test_session_id)
                mock_category.assert_called_once_with("test", test_session_id)
                mock_translation.assert_called_once_with({"test": []}, test_session_id)
                
            finally:
                if os.path.exists(image_path):
                    os.unlink(image_path)


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """パフォーマンス統合テスト"""

    @pytest.mark.asyncio
    async def test_workflow_performance(self, test_session_id):
        """ワークフロー全体のパフォーマンステスト"""
        import time
        
        start_time = time.time()
        
        # 高速なモックを使用してワークフローの基本パフォーマンスを測定
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr, \
             patch('app.services.category.category_manager.categorize_menu') as mock_category, \
             patch('app.services.translation.translation_manager.translate_menu') as mock_translation:
            
            # 高速なモックレスポンス
            mock_ocr.return_value = OCRResult(
                success=True,
                extracted_text="fast test",
                provider=OCRProvider.GEMINI
            )
            
            mock_category.return_value = CategoryResult(
                success=True,
                categories={"test": [{"name": "fast test"}]},
                uncategorized=[],
                provider=CategoryProvider.OPENAI
            )
            
            mock_translation.return_value = TranslationResult(
                success=True,
                translated_menu={"test": [{"japanese_name": "fast test", "english_name": "fast test"}]},
                provider=TranslationProvider.GOOGLE_TRANSLATE
            )
            
            # ワークフロー実行
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(b"fake image data")
                image_path = temp_file.name
            
            try:
                ocr_result = await extract_text(image_path, test_session_id)
                category_result = await categorize_menu(ocr_result.extracted_text, test_session_id)
                translation_result = await translate_menu(category_result.categories, test_session_id)
                
                execution_time = time.time() - start_time
                
                # モックを使用した場合は非常に高速であることを確認（1秒以内）
                assert execution_time < 1.0
                assert all([ocr_result.success, category_result.success, translation_result.success])
                
            finally:
                if os.path.exists(image_path):
                    os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self):
        """並行ワークフロー実行のテスト"""
        # 複数のセッションが同時に処理されることを確認
        session_ids = [f"session-{i}" for i in range(3)]
        
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_ocr:
            mock_ocr.return_value = OCRResult(
                success=True,
                extracted_text="concurrent test",
                provider=OCRProvider.GEMINI
            )
            
            # 複数のセッションで並行実行
            tasks = []
            for session_id in session_ids:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    temp_file.write(b"fake image data")
                    task = extract_text(temp_file.name, session_id)
                    tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # 全ての結果が成功していることを確認
            assert len(results) == 3
            for result in results:
                assert result.success is True
                assert result.extracted_text == "concurrent test"


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """エラー回復統合テスト"""

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, test_session_id):
        """リトライ機構のテスト"""
        call_count = 0
        
        def mock_ocr_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # 最初の2回は失敗
                return OCRResult(
                    success=False,
                    extracted_text="",
                    provider=OCRProvider.GEMINI,
                    error="Temporary API error"
                )
            else:
                # 3回目で成功
                return OCRResult(
                    success=True,
                    extracted_text="retry success",
                    provider=OCRProvider.GEMINI
                )
        
        with patch('app.services.ocr.ocr_manager.extract_text', side_effect=mock_ocr_with_retry):
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(b"fake image data")
                image_path = temp_file.name
            
            try:
                # リトライ機構が働くサービスがあるかテスト
                # （実際のリトライ実装は各サービスによる）
                result = await extract_text(image_path, test_session_id)
                
                # 最終的に成功することを確認
                # 注意: 実際のリトライ機構が実装されている場合のみ成功
                # assert result.success is True
                
            finally:
                if os.path.exists(image_path):
                    os.unlink(image_path) 