"""
Complete Pipeline Test Script - Real Image Processing
実際のテスト画像を使用したOCR → Categorize → Translate → DB Verification の完全テスト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any

from app_2.pipelines.pipeline_runner import get_menu_processing_pipeline
from app_2.services.ocr_service import get_ocr_service
from app_2.services.mapping_service import get_menu_mapping_categorize_service
from app_2.services.translate_service import get_translate_service
from app_2.services.dependencies import get_menu_repository, get_session_repository
from app_2.core.database import async_session_factory
from app_2.utils.logger import get_logger

logger = get_logger("complete_pipeline_test")


class CompletePipelineTest:
    """完全なパイプラインテストクラス"""
    
    def __init__(self):
        self.test_image_path = Path(__file__).parent.parent / "tests" / "data" / "menu_test.webp"
        self.session_id = str(uuid.uuid4())
        
    async def run_complete_test(self):
        """完全なパイプラインテストを実行"""
        print("🚀 Complete Pipeline Test - 実画像処理テスト開始")
        print("=" * 80)
        
        if not self.test_image_path.exists():
            print(f"❌ テスト画像が見つかりません: {self.test_image_path}")
            return False
        
        print(f"📸 使用画像: {self.test_image_path.name}")
        print(f"🆔 セッションID: {self.session_id}")
        print(f"📊 画像サイズ: {self.test_image_path.stat().st_size} bytes")
        
        try:
            # Step 1: OCR テスト
            ocr_result = await self._test_ocr_step()
            
            # Step 2: カテゴライズ テスト  
            categorize_result = await self._test_categorize_step(ocr_result)
            
            # Step 3: DB保存 テスト
            saved_entities = await self._test_db_save_step(categorize_result)
            
            # Step 4: 翻訳処理 テスト
            translation_result = await self._test_translation_step(saved_entities)
            
            # Step 5: 最終検証
            await self._verify_final_results(saved_entities)
            
            print("\n🎉 Complete Pipeline Test - 全ステップ成功!")
            return True
            
        except Exception as e:
            logger.error(f"Complete pipeline test failed: {e}")
            print(f"❌ テスト失敗: {e}")
            return False
    
    async def _test_ocr_step(self) -> List[Dict[str, Any]]:
        """Step 1: OCR処理テスト"""
        print("\n📋 Step 1: OCR Processing Test")
        print("-" * 40)
        
        with open(self.test_image_path, 'rb') as f:
            image_data = f.read()
        
        ocr_service = get_ocr_service()
        ocr_result = await ocr_service.extract_text_with_positions(
            image_data, level="paragraph"
        )
        
        print(f"✅ OCR完了: {len(ocr_result)} 個のテキスト要素を抽出")
        
        # サンプル結果表示
        if ocr_result:
            print("📝 抽出されたテキスト例:")
            for i, element in enumerate(ocr_result[:5]):  # 最初の5個を表示
                text = element.get("text", "")
                x = element.get("x_center", 0)
                y = element.get("y_center", 0)
                print(f"   {i+1}. '{text}' (x:{x:.1f}, y:{y:.1f})")
            
            if len(ocr_result) > 5:
                print(f"   ... 他 {len(ocr_result) - 5} 個")
        
        return ocr_result
    
    async def _test_categorize_step(self, ocr_result: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 2: カテゴライズ処理テスト"""
        print("\n🗂️ Step 2: Categorization Test")
        print("-" * 40)
        
        categorize_service = get_menu_mapping_categorize_service()
        categorize_result = await categorize_service.categorize_mapping_data(
            ocr_result, level="paragraph"
        )
        
        print("✅ カテゴライズ完了")
        
        # カテゴリ情報表示
        if "menu" in categorize_result and "categories" in categorize_result["menu"]:
            categories = categorize_result["menu"]["categories"]
            print(f"📁 発見されたカテゴリ: {len(categories)} 個")
            
            total_items = 0
            for i, category in enumerate(categories):
                cat_name = category.get("name", f"Unknown_{i}")
                items_count = len(category.get("items", []))
                total_items += items_count
                print(f"   {i+1}. {cat_name}: {items_count} アイテム")
                
                # アイテム例表示
                for j, item in enumerate(category.get("items", [])[:3]):
                    name = item.get("name", "")
                    price = item.get("price", "")
                    print(f"      - {name} {price}")
                    
                if len(category.get("items", [])) > 3:
                    print(f"      ... 他 {len(category.get('items', [])) - 3} 個")
            
            print(f"📊 総メニューアイテム数: {total_items} 個")
        
        return categorize_result
    
    async def _test_db_save_step(self, categorize_result: Dict[str, Any]) -> List:
        """Step 3: DB保存テスト"""
        print("\n💾 Step 3: Database Save Test")
        print("-" * 40)
        
        from app_2.services.menu_save_service import create_menu_save_service
        from app_2.domain.entities.session_entity import SessionEntity, SessionStatus
        
        # まずセッションを作成
        print("📋 セッション作成中...")
        async with async_session_factory() as db_session:
            session_repo = get_session_repository(db_session)
            session_entity = SessionEntity(
                session_id=self.session_id,
                status=SessionStatus.PROCESSING,
                menu_ids=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await session_repo.save(session_entity)
            print(f"   セッション作成完了: {self.session_id}")
        
        # メニューアイテム保存
        print("📋 メニューアイテム保存中...")
        async with async_session_factory() as db_session:
            menu_repository = get_menu_repository(db_session)
            menu_save_service = create_menu_save_service(menu_repository)
            
            saved_entities = await menu_save_service.save_categorized_menu_with_session_id(
                categorize_result, self.session_id
            )
        
        print(f"✅ DB保存完了: {len(saved_entities)} 個のメニューアイテムを保存")
        
        # セッション更新
        if saved_entities:
            print("📋 セッション更新中...")
            menu_ids = [entity.id for entity in saved_entities]
            async with async_session_factory() as db_session:
                session_repo = get_session_repository(db_session)
                session_entity = await session_repo.get_by_id(self.session_id)
                if session_entity:
                    session_entity.menu_ids = menu_ids
                    session_entity.updated_at = datetime.utcnow()
                    await session_repo.update(session_entity)
                    print(f"   セッション更新完了: {len(menu_ids)} 個のメニューID登録")
        
        # 保存されたエンティティ情報表示
        print("📋 保存されたメニューアイテム:")
        for i, entity in enumerate(saved_entities[:10]):  # 最初の10個を表示
            print(f"   {i+1}. ID: {entity.id}")
            print(f"       名前: {entity.name}")
            print(f"       カテゴリ: {entity.category}")
            print(f"       価格: {entity.price}")
            print()
            
        if len(saved_entities) > 10:
            print(f"   ... 他 {len(saved_entities) - 10} 個")
        
        return saved_entities
    
    async def _test_translation_step(self, saved_entities: List) -> Dict[str, Any]:
        """Step 4: 翻訳処理テスト"""
        print("\n🌍 Step 4: Translation Test")
        print("-" * 40)
        
        translate_service = get_translate_service()
        
        # 最初の3個のエンティティを翻訳テスト
        test_entities = saved_entities[:3]
        translation_results = []
        
        for i, entity in enumerate(test_entities):
            print(f"翻訳中 {i+1}/{len(test_entities)}: {entity.name}")
            
            try:
                # メニューアイテムデータ準備
                menu_data = {
                    "name": entity.name,
                    "category": entity.category,
                    "price": entity.price
                }
                
                # 翻訳実行
                translated = await translate_service.translate_menu_data(
                    menu_data, target_language="en"
                )
                
                # DB更新
                async with async_session_factory() as db_session:
                    menu_repository = get_menu_repository(db_session)
                    
                    # エンティティ取得と更新
                    existing_entity = await menu_repository.get_by_id(entity.id)
                    if existing_entity:
                        existing_entity.translation = translated.get("name", entity.name)
                        existing_entity.category_translation = translated.get("category", entity.category)
                        
                        updated_entity = await menu_repository.update(existing_entity)
                        
                        result = {
                            "original": {
                                "name": entity.name,
                                "category": entity.category
                            },
                            "translated": {
                                "name": updated_entity.translation,
                                "category": updated_entity.category_translation
                            },
                            "status": "success"
                        }
                        
                        print(f"   ✅ {entity.name} → {updated_entity.translation}")
                        translation_results.append(result)
                    else:
                        print(f"   ❌ エンティティが見つかりません: {entity.id}")
                        translation_results.append({
                            "original": {"name": entity.name},
                            "status": "entity_not_found"
                        })
                        
            except Exception as e:
                print(f"   ❌ 翻訳失敗: {e}")
                translation_results.append({
                    "original": {"name": entity.name},
                    "status": "translation_failed",
                    "error": str(e)
                })
        
        successful_translations = len([r for r in translation_results if r.get("status") == "success"])
        print(f"\n✅ 翻訳テスト完了: {successful_translations}/{len(test_entities)} 個成功")
        
        return {
            "tested_count": len(test_entities),
            "successful_count": successful_translations,
            "results": translation_results
        }
    
    async def _verify_final_results(self, saved_entities: List):
        """Step 5: 最終検証"""
        print("\n🔍 Step 5: Final Verification")
        print("-" * 40)
        
        async with async_session_factory() as db_session:
            menu_repository = get_menu_repository(db_session)
            
            print("データベース内容検証:")
            verified_count = 0
            translation_count = 0
            
            for entity in saved_entities[:5]:  # 最初の5個を検証
                db_entity = await menu_repository.get_by_id(entity.id)
                if db_entity:
                    verified_count += 1
                    if db_entity.translation:
                        translation_count += 1
                    
                    print(f"   ✅ ID: {db_entity.id}")
                    print(f"       原文: {db_entity.name}")
                    print(f"       翻訳: {db_entity.translation or '未翻訳'}")
                    print(f"       カテゴリ: {db_entity.category} → {db_entity.category_translation or '未翻訳'}")
                    print()
                else:
                    print(f"   ❌ エンティティが見つかりません: {entity.id}")
            
            print(f"📊 検証結果:")
            print(f"   - 検証したアイテム: {min(5, len(saved_entities))} 個")
            print(f"   - DB内存在確認: {verified_count} 個")
            print(f"   - 翻訳済み: {translation_count} 個")


async def main():
    """メイン実行関数"""
    test = CompletePipelineTest()
    
    print("🔬 Complete Pipeline Test - Menu Processor v2")
    print("=" * 80)
    print("実際のテスト画像を使用したフルパイプラインテスト")
    print("OCR → Categorize → DB Save → Translation → Verification")
    print()
    
    try:
        success = await test.run_complete_test()
        
        if success:
            print("\n" + "=" * 80)
            print("🎉 Complete Pipeline Test - SUCCESS!")
            print("全ステップが正常に完了しました")
        else:
            print("\n" + "=" * 80)
            print("❌ Complete Pipeline Test - FAILED!")
            print("一部のステップで問題が発生しました")
        
        return success
        
    except KeyboardInterrupt:
        print("\n⏹️ テスト中断")
        return False
    except Exception as e:
        print(f"\n💥 予期しないエラー: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 