# 📋 各Stage ワーカー活用 詳細設計

## 🎯 Stage 1: OCR処理のワーカー活用

### 現在の問題点
- FastAPIプロセスでGemini API呼び出し（ブロッキング）
- 大きな画像での処理時間が長い
- エラー時のリトライが困難

### 理想的なワーカー設計

#### パターンA: シンプルワーカー移行（即座実装可能）
```python
# app/tasks/ocr_tasks.py
@celery_app.task(bind=True, name="ocr_simple_task")
def process_ocr_simple(self, image_path, session_id=None):
    """OCR処理をワーカーで実行"""
    try:
        # 進行状況更新
        self.update_state(state='PROGRESS', meta={'stage': 'ocr', 'progress': 0})
        
        # Gemini API呼び出し（既存サービス活用）
        from app.services.ocr import extract_text
        result = await_sync(extract_text(image_path, session_id))
        
        # 進行状況更新
        self.update_state(state='PROGRESS', meta={'stage': 'ocr', 'progress': 100})
        
        return {
            'success': result.success,
            'extracted_text': result.extracted_text,
            'metadata': result.metadata
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**メリット**: 
- FastAPIリソース解放
- エラー時自動リトライ
- ワーカーレベルでの負荷分散

#### パターンB: 画像分割並列処理（高度な最適化）
```python
@celery_app.task(bind=True, name="ocr_parallel_task")
def process_ocr_parallel(self, image_path, session_id=None):
    """大きな画像を分割して並列OCR処理"""
    try:
        # 1. 画像を分析してサイズ・複雑度を判定
        image_info = analyze_image_complexity(image_path)
        
        if image_info['needs_splitting']:
            # 2. 画像を複数領域に分割
            image_chunks = split_image_intelligently(image_path, image_info)
            
            # 3. 各チャンクを並列処理
            chunk_tasks = []
            for i, chunk in enumerate(image_chunks):
                task = process_ocr_chunk.delay(chunk, i, session_id)
                chunk_tasks.append(task)
            
            # 4. 結果を統合
            chunk_results = [task.get() for task in chunk_tasks]
            final_text = merge_ocr_results(chunk_results, image_info)
            
        else:
            # 小さな画像は通常処理
            final_text = process_single_ocr(image_path)
        
        return {'success': True, 'extracted_text': final_text}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**メリット**: 
- 大きな画像での劇的高速化
- 複雑なメニューでの精度向上
- 部分失敗時の回復力

---

## 🏷️ Stage 2: カテゴライズのワーカー活用

### 現在の問題点
- 大量テキストでのOpenAI API制限
- 単一APIコールでの処理時間
- 複雑なメニューでの分類精度

### 理想的なワーカー設計

#### パターンA: テキスト分割処理
```python
@celery_app.task(bind=True, name="categorization_smart_task")
def categorize_menu_smart(self, extracted_text, session_id=None):
    """テキスト量に応じて分割・並列カテゴライズ"""
    try:
        # 1. テキスト量とメニュー複雑度を分析
        text_analysis = analyze_menu_text(extracted_text)
        
        if text_analysis['needs_chunking']:
            # 2. メニュー構造を保持して分割
            text_chunks = split_menu_text_intelligently(
                extracted_text, 
                max_tokens=text_analysis['optimal_chunk_size']
            )
            
            # 3. 各チャンクを並列カテゴライズ
            chunk_tasks = []
            for i, chunk in enumerate(text_chunks):
                task = categorize_text_chunk.delay(chunk, i, session_id)
                chunk_tasks.append(task)
            
            # 4. 結果をマージして重複解決
            chunk_results = [task.get() for task in chunk_tasks]
            final_categories = merge_categorization_results(chunk_results)
            
        else:
            # 小さなメニューは通常処理
            final_categories = categorize_single_text(extracted_text)
        
        return {
            'success': True,
            'categories': final_categories['categories'],
            'uncategorized': final_categories['uncategorized']
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

#### パターンB: 階層的カテゴライズ
```python
@celery_app.task(bind=True, name="categorization_hierarchical_task")
def categorize_hierarchical(self, extracted_text, session_id=None):
    """階層的にカテゴライズして精度向上"""
    try:
        # 1. 第一段階：大まかな分類
        primary_categories = rough_categorization(extracted_text)
        
        # 2. 第二段階：各大分類を詳細分類
        detailed_tasks = []
        for category, items in primary_categories.items():
            task = detail_categorize_items.delay(category, items, session_id)
            detailed_tasks.append(task)
        
        # 3. 結果統合
        detailed_results = [task.get() for task in detailed_tasks]
        final_categories = combine_hierarchical_results(detailed_results)
        
        return {'success': True, 'categories': final_categories}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## 🌍 Stage 3: 翻訳の並列化

### 現在の問題点
- カテゴリを逐次処理
- Google Translate APIの制限
- 大量アイテムでの処理時間

### 理想的なワーカー設計

#### パターンA: カテゴリレベル並列処理（推奨）
```python
@celery_app.task(bind=True, name="translation_parallel_task")
def translate_menu_parallel(self, categorized_data, session_id=None):
    """カテゴリごとに並列翻訳処理"""
    try:
        # 1. カテゴリごとにワーカータスクを作成
        translation_tasks = []
        
        for category_name, items in categorized_data.items():
            task = translate_category_worker.delay(
                category_name, items, session_id
            )
            translation_tasks.append((category_name, task))
        
        # 2. 並列実行して結果を収集
        translated_categories = {}
        
        for category_name, task in translation_tasks:
            try:
                result = task.get(timeout=60)  # 1分タイムアウト
                if result['success']:
                    translated_categories[category_name] = result['translated_items']
                else:
                    # 個別失敗時は元データで代替
                    translated_categories[category_name] = categorized_data[category_name]
            except Exception as e:
                # タスク失敗時のフォールバック
                translated_categories[category_name] = categorized_data[category_name]
        
        return {
            'success': True,
            'translated_categories': translated_categories,
            'translation_method': 'parallel_worker_processing'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@celery_app.task(bind=True, name="translate_category_worker")
def translate_category_worker(self, category_name, items, session_id=None):
    """単一カテゴリをワーカーで翻訳"""
    try:
        # 1. Google Translate APIで一括翻訳
        translated_items = []
        
        for item in items:
            try:
                # Google Translate API呼び出し
                translated_item = translate_single_item_google(item)
                translated_items.append(translated_item)
                
            except Exception as e:
                # 個別アイテム失敗時はOpenAI フォールバック
                try:
                    translated_item = translate_single_item_openai(item)
                    translated_items.append(translated_item)
                except Exception as e2:
                    # 両方失敗時は元データ保持
                    translated_items.append(item)
        
        return {
            'success': True,
            'translated_items': translated_items,
            'category': category_name
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e), 'category': category_name}
```

**期待効果**: 
- カテゴリ数 × 並列度の高速化
- 個別失敗時の部分回復
- API制限の分散

---

## 📝 Stage 4: 詳細説明のチャンク化と画像連携

### 現在の実装状況
- 既にチャンク並列処理実装済み
- 改善点：画像生成との連携

### 理想的なワーカー設計

#### パターンA: 説明完了→即座画像生成
```python
@celery_app.task(bind=True, name="description_with_image_pipeline")
def process_description_with_immediate_images(self, translated_data, session_id=None):
    """詳細説明とパイプライン化された画像生成"""
    try:
        # 1. カテゴリごとにチャンク分割
        all_chunks = create_description_chunks(translated_data)
        
        # 2. 各チャンクを並列処理（既存機能活用）
        description_tasks = []
        
        for chunk_info in all_chunks:
            # 説明生成タスクを開始
            task = process_description_chunk_with_callback.delay(
                chunk_info['data'], chunk_info, session_id
            )
            description_tasks.append(task)
        
        # 3. 完了したチャンクから順次画像生成開始
        completed_descriptions = {}
        image_generation_jobs = []
        
        for task in description_tasks:
            chunk_result = task.get()
            if chunk_result['success']:
                # 説明完了→即座に画像生成開始
                image_job = generate_images_for_chunk.delay(
                    chunk_result['items'], session_id
                )
                image_generation_jobs.append(image_job)
                
                # 説明結果を保存
                category = chunk_result['category']
                if category not in completed_descriptions:
                    completed_descriptions[category] = []
                completed_descriptions[category].extend(chunk_result['items'])
        
        # 4. 全画像生成完了を待機
        final_images = {}
        for image_job in image_generation_jobs:
            image_result = image_job.get()
            if image_result['success']:
                final_images.update(image_result['images'])
        
        return {
            'success': True,
            'final_menu': completed_descriptions,
            'images_generated': final_images,
            'pipeline_optimization': True
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**メリット**:
- 説明完了したアイテムから即座に画像生成
- 全体処理時間の30-50%短縮
- リアルタイム進捗の向上

---

## 🎨 Stage 5: 画像生成の更なる最適化

### 現在の実装状況
- 既にCelery非同期処理実装済み
- チャンク並列処理も実装済み

### 追加最適化案

#### パターンA: 優先度付きキュー
```python
@celery_app.task(bind=True, name="prioritized_image_generation")
def generate_images_prioritized(self, menu_items, session_id=None, priority='normal'):
    """優先度付き画像生成"""
    # 人気カテゴリ（前菜、メイン）を優先
    # ユーザーが見る可能性の高い順序で生成
    
    prioritized_items = sort_by_generation_priority(menu_items)
    return process_image_generation_queue(prioritized_items, session_id)
```

#### パターンB: 段階的品質向上
```python
@celery_app.task(bind=True, name="progressive_image_generation")
def generate_images_progressive(self, menu_items, session_id=None):
    """段階的品質向上（低品質→高品質）"""
    # 1. 低品質版を高速生成（即座表示用）
    # 2. 高品質版をバックグラウンド生成（置き換え用）
    
    # フロントエンドでは段階的表示
    pass
```

---

## 🔧 実装の優先順位

### 今週実装（即座効果）
1. **Stage 3翻訳並列化**：カテゴリレベル並列処理
2. **Stage 4パイプライン**：説明→即座画像生成
3. **設定最適化**：ワーカー数、チャンクサイズ調整

### 来週実装（中期効果）
4. **Stage 2スマート分割**：大量テキスト対応
5. **Stage 1ワーカー移行**：OCR処理の非同期化
6. **エラー処理強化**：フォールバック機能

### 実装時の注意点
- **フロントエンド影響なし**：レスポンス形式完全保持
- **段階的テスト**：各Stage個別にテスト
- **フォールバック必須**：ワーカー失敗時の同期処理

この設計について、どの部分から実装を始めたいですか？特に気になるStageや、優先したい最適化はありますか？ 