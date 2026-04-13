import os
import json
from typing import List, Dict, Tuple
from collections import defaultdict

import httpx
import openai
import anthropic

from .config import AI_BATCH_SIZE, AI_MODEL, AI_PROVIDER, OPENAI_BASE_URL, OUTPUT_DIR
from .storage import Storage


class AIAnalyzer:
    def __init__(self, storage):
        self.storage = storage
        self._setup_client()

    def _setup_client(self):
        # Clear proxy settings to avoid httpx compatibility issues
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(var, None)

        if AI_PROVIDER == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            self.model = AI_MODEL or "claude-3-haiku-20240307"
        else:
            base_url = OPENAI_BASE_URL or None
            self.client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=base_url
            )
            self.model = AI_MODEL or "gpt-4o-mini"

    def _is_useful_comment(self, content: str) -> bool:
        """Filter out useless/spam comments."""
        if not content or len(content.strip()) < 5:
            return False

        # Remove very short comments
        if len(content) < 5:
            return False

        # Spam patterns
        spam_patterns = [
            '都被做烂了', '已经烂大街了', '到处都是', '做烂了',
            '哈哈', '呵呵', '666', '牛', '赞', '好厉害',
            'mark', '马克', '打卡', '路过', '楼上',
            '是的', '对的', '确实', '赞同', '没错',
            '我也想要', '我也想', '我也想做',
        ]

        content_lower = content.lower()
        for pattern in spam_patterns:
            if pattern in content_lower:
                # Allow if it's longer than 20 chars (might be a real comment)
                if len(content) < 20:
                    return False

        # Single word responses
        if len(content.strip()) < 10 and not any(c in content for c in '，。！？'):
            return False

        return True

    def aggregate_comments(self, comments: List[Dict]) -> List[Dict]:
        """
        Aggregate similar comments into clustered viewpoints.
        Returns list of aggregated views with their frequency.
        """
        if not comments:
            return []

        # Filter out useless comments first
        useful_comments = [c for c in comments if self._is_useful_comment(c.get('content', ''))]
        print(f"Filtered {len(comments) - len(useful_comments)} useless comments, {len(useful_comments)} remaining")

        # Simple keyword-based aggregation
        # In production, could use embeddings + clustering
        groups = defaultdict(list)
        for c in useful_comments:
            content = c.get('content', '').lower().strip()
            if not content:
                continue

            # Simple: group by first 50 chars (crude but fast)
            key = content[:50]
            groups[key].append(c)

        aggregated = []
        for key, group in groups.items():
            # Use the first comment as representative
            representative = group[0]
            aggregated.append({
                'view': representative['content'],
                'count': len(group),
                'like_count': sum(c.get('like_count', 0) for c in group),
                'comment_ids': [c['id'] for c in group]
            })

        # Sort by like_count descending
        aggregated.sort(key=lambda x: x['like_count'], reverse=True)
        return aggregated[:50]  # Keep top 50 aggregated views

    def clean_comments_batch(self, comments: List[Dict]) -> List[Dict]:
        """Send comments to AI for cleaning - filter out irrelevant ones, keep useful ideas."""
        if not comments:
            return []

        # Format comments for AI
        comments_text = "\n".join(
            f"[{i+1}] 用户:{c.get('user','')} | 点赞:{c.get('like_count',0)} | 评论:{c.get('content','')}"
            for i, c in enumerate(comments)
        )

        prompt = f"""你是一个数据清洗助手。请从以下小红书评论中筛选出有价值的用户需求和创意建议。

需要保留的评论类型：
- 用户提出的具体功能需求（如"想要一个XXX功能的app"）
- 用户描述的问题或痛点
- 用户建议的解决方案或想法
- 有建设性的意见和反馈

需要过滤的评论：
- 无意义的感叹词（哈哈、666、牛、赞等）
- 简短的赞同或附和（是的、对、没错等）
- 打卡、mark、路过等无意义回复
- 完全无关的内容
- 太短没有信息量的评论

评论列表：
{comments_text}

请返回清洗后的评论列表（JSON数组格式），每个元素包含原评论的关键信息和可行性评分：
返回格式：
[
  {{"original_content": "原评论内容", "user": "用户名", "like_count": 点赞数, "cleaned_view": "清洗后的核心需求/创意", "feasibility_score": 1-5分}},
  ...
]

只返回JSON，不需要其他解释。评分标准：5分=非常有潜力的创意，1分=不太可行。"""

        try:
            if AI_PROVIDER == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000
                )
                content = response.choices[0].message.content

            # Remove think tags before parsing JSON
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

            # Parse AI response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start == -1 or json_end == 0:
                print("AI response did not contain JSON")
                return []

            json_str = content[json_start:json_end]
            parsed = json.loads(json_str)
            return parsed

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI cleaning response: {e}")
            print(f"Content: {content[:500] if content else 'empty'}")
            return []
        except Exception as e:
            print(f"Error cleaning comments: {e}")
            return []

    def analyze_note(self, note_id: str) -> List[Dict]:
        """Analyze all comments for a note."""
        # Get unanalyzed comments
        comments = self.storage.get_comments_for_note(note_id)
        if not comments:
            return []

        # Aggregate comments
        aggregated_views = self.aggregate_comments(comments)

        if not aggregated_views:
            return []

        # Batch process with AI
        results = []
        for i in range(0, len(aggregated_views), AI_BATCH_SIZE):
            batch = aggregated_views[i:i + AI_BATCH_SIZE]
            batch_results = self._analyze_batch(note_id, batch)
            results.extend(batch_results)

        return results

    def _analyze_batch(self, note_id: str, views: List[Dict]) -> List[Dict]:
        """Send a batch of views to AI for feasibility analysis."""
        prompt = self._build_feasibility_prompt(views)

        if AI_PROVIDER == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            content = response.choices[0].message.content

        return self._parse_ai_response(content, views, note_id)

    def _build_feasibility_prompt(self, views: List[Dict]) -> str:
        """Build prompt for feasibility analysis."""
        views_text = "\n".join(
            f"- [{v['count']}人赞同] {v['view']}"
            for v in views
        )

        prompt = f"""你是一个产品创意可行性分析师。请分析以下从社交媒体评论中收集的点子，评估每个点子的可行性和商业潜力。

评论聚合观点：
{views_text}

请对每个观点给出：
1. 可行性评分 (1-5分，5分最高)
2. 简短理由

返回格式（JSON数组）：
[
  {{"view": "观点内容", "score": 评分, "reasoning": "理由"}},
  ...
]

只返回JSON，不需要其他解释。"""
        return prompt

    def _parse_ai_response(self, content: str, views: List[Dict], note_id: str) -> List[Dict]:
        """Parse AI response and save results."""
        results = []

        try:
            # Remove think tags before parsing JSON
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

            # Extract JSON from response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start == -1 or json_end == 0:
                return []

            json_str = content[json_start:json_end]
            parsed = json.loads(json_str)

            # Map results back to views and save
            for item in parsed:
                view_text = item.get('view', '')
                score = item.get('score', 0)
                reasoning = item.get('reasoning', '')

                # Find matching view
                matched_view = None
                matched_ids = []
                for v in views:
                    if v['view'] == view_text or view_text in v['view']:
                        matched_view = v
                        matched_ids = v['comment_ids']
                        break

                if matched_view and score >= 3:
                    self.storage.save_ai_result(
                        note_id=note_id,
                        aggregated_view=view_text,
                        feasibility_score=score,
                        reasoning=reasoning
                    )
                    if matched_ids:
                        self.storage.mark_comments_analyzed(matched_ids)

                    results.append({
                        'view': view_text,
                        'score': score,
                        'reasoning': reasoning,
                        'count': matched_view['count'] if matched_view else 0
                    })

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response: {e}")
            print(f"Content: {content[:500]}")
        except Exception as e:
            print(f"Error processing AI response: {e}")

        return results

    def analyze_all_notes(self, keyword: str = None) -> Dict:
        """Analyze all notes for a keyword or all notes if no keyword."""
        summary = {'notes_analyzed': 0, 'results_found': 0}

        if keyword:
            keyword_id = self.storage.get_keyword_id(keyword)
            if not keyword_id:
                return summary
            note_ids = self.storage.get_note_ids_for_keyword(keyword_id)
        else:
            # Get all keywords
            keywords = self.storage.get_all_keywords()
            note_ids = []
            for kw in keywords:
                note_ids.extend(
                    self.storage.get_note_ids_for_keyword(kw['id'])
                )

        for note_id in note_ids:
            results = self.analyze_note(note_id)
            if results:
                summary['notes_analyzed'] += 1
                summary['results_found'] += len(results)

        return summary

    def export_high_feasibility(self, min_score: int = 3, output_file: str = None) -> List[Dict]:
        """Export all high feasibility results."""
        results = self.storage.get_ai_results(min_score=min_score)

        if output_file:
            output_path = OUTPUT_DIR / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"Exported {len(results)} results to {output_path}")

        return results


def analyze_note_sync(note_id: str, storage: Storage) -> List[Dict]:
    """Synchronous wrapper for analyze_note."""
    analyzer = AIAnalyzer(storage)
    return analyzer.analyze_note(note_id)
