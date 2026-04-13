#!/usr/bin/env python3
"""
分析小红书创意点子，生成详细的可行性分析 Excel 报告
"""
import os
import sys
import csv
import json
import re
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import AI_MODEL, AI_PROVIDER, OPENAI_BASE_URL
from src.ai_analyzer import AIAnalyzer

import httpx
import openai
import anthropic


def setup_ai_client():
    """Setup AI client."""
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(var, None)

    if AI_PROVIDER == "anthropic":
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = AI_MODEL or "claude-3-haiku-20240307"
    else:
        base_url = OPENAI_BASE_URL or None
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url
        )
        model = AI_MODEL or "gpt-4o-mini"

    return client, model


def call_ai_analyze(client, model, idea_text, provider="openai"):
    """Call AI to analyze a single idea."""
    prompt = f"""你是一个专业的App产品可行性分析师。请分析以下App创意的详细可行性报告。

App创意：{idea_text}

请返回JSON格式的详细分析报告，包含以下维度：
1. 可行性评分 (1-5分，5分最高)
2. 推荐搭载平台 (iOS/Android/双端/小程序/H5)
3. 开发成本估算：
   - 开发周期（人/天）
   - 服务器成本（元/月）
   - Token/AI成本（元/月，如果用到AI）
   - 总开发成本估算（元）
4. 所属行业领域
5. 目标用户群体
6. 推广难度 (1-5，5最难)
7. 变现方式建议
8. 核心竞争优势
9. 主要风险点
10. 简短理由（1-2句话）

返回格式（JSON）：
{{
  "idea": "原始创意摘要",
  "feasibility_score": 4,
  "platform": "iOS+Android双端",
  "dev_days": 60,
  "server_cost_monthly": 500,
  "token_cost_monthly": 200,
  "total_cost_estimate": 50000,
  "industry": "健康医疗",
  "target_users": "健身爱好者、注重饮食管理的都市白领",
  "promotion_difficulty": 3,
  "monetization": "订阅制+增值服务",
  "advantage": "差异化功能+垂直细分市场",
  "risk": "医疗资质门槛",
  "reasoning": "结合AI营养分析和体检数据有差异化，但需注意医疗合规"
}}

只返回JSON，不需要其他解释。"""

    try:
        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            content = response.choices[0].message.content

        # Remove think tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

        # Extract JSON
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            print(f"  [WARN] No JSON found in response")
            return None

        json_str = content[json_start:json_end]
        return json.loads(json_str)

    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] AI call failed: {e}")
        return None


def read_csv_ideas(csv_path):
    """Read ideas from CSV file."""
    ideas = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned_view = row.get('cleaned_view', '').strip()
            if cleaned_view:
                ideas.append({
                    'note_id': row.get('note_id', ''),
                    'note_title': row.get('note_title', ''),
                    'user': row.get('user', ''),
                    'like_count': row.get('like_count', 0),
                    'cleaned_view': cleaned_view,
                    'original_feasibility': row.get('feasibility_score', '')
                })
    return ideas


def read_all_csv_ideas(output_dir):
    """Read all idea CSV files from output directory."""
    ideas = []
    for csv_file in output_dir.glob("*_comments.csv"):
        print(f"Reading {csv_file.name}...")
        file_ideas = read_csv_ideas(csv_file)
        ideas.extend(file_ideas)
        print(f"  Found {len(file_ideas)} ideas")
    return ideas


def write_excel(ideas_with_analysis, output_path):
    """Write analysis results to Excel-like CSV."""
    headers = [
        '序号',
        '原始创意',
        '可行性评分',
        '推荐平台',
        '开发周期(人天)',
        '服务器成本/月(元)',
        'Token成本/月(元)',
        '总成本估算(元)',
        '所属行业',
        '目标用户',
        '推广难度(1-5)',
        '变现方式',
        '核心优势',
        '主要风险',
        '分析理由'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i, item in enumerate(ideas_with_analysis, 1):
            analysis = item.get('analysis') or {}
            writer.writerow([
                i,
                item.get('cleaned_view', ''),
                analysis.get('feasibility_score', ''),
                analysis.get('platform', ''),
                analysis.get('dev_days', ''),
                analysis.get('server_cost_monthly', ''),
                analysis.get('token_cost_monthly', ''),
                analysis.get('total_cost_estimate', ''),
                analysis.get('industry', ''),
                analysis.get('target_users', ''),
                analysis.get('promotion_difficulty', ''),
                analysis.get('monetization', ''),
                analysis.get('advantage', ''),
                analysis.get('risk', ''),
                analysis.get('reasoning', '')
            ])

    print(f"\nExcel报告已生成: {output_path}")


async def analyze_ideas():
    """Main analysis flow."""
    print("=" * 60)
    print("小红书App创意可行性分析")
    print("=" * 60)

    # Setup AI client
    client, model = setup_ai_client()
    print(f"AI模型: {model}")
    print(f"AI提供商: {AI_PROVIDER}")

    # Read all idea CSV files
    output_dir = Path(__file__).parent.parent / "output"
    ideas = read_all_csv_ideas(output_dir)
    print(f"\n共读取到 {len(ideas)} 条创意\n")

    # Analyze each idea
    results = []
    for i, idea in enumerate(ideas, 1):
        print(f"[{i}/{len(ideas)}] 正在分析: {idea['cleaned_view'][:40]}...")

        analysis = call_ai_analyze(client, model, idea['cleaned_view'], AI_PROVIDER)

        if analysis:
            print(f"  可行性: {analysis.get('feasibility_score', 'N/A')} | "
                  f"平台: {analysis.get('platform', 'N/A')} | "
                  f"成本: {analysis.get('total_cost_estimate', 'N/A')}元")
            idea['analysis'] = analysis
        else:
            print(f"  [跳过] AI分析失败")
            idea['analysis'] = {
                'feasibility_score': idea['original_feasibility'],
                'reasoning': 'AI分析失败'
            }

        results.append(idea)

        # Delay between calls to avoid rate limit
        if i < len(ideas):
            await asyncio.sleep(2)

    # Write to Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(__file__).parent.parent / "output" / f"创意可行性分析_{timestamp}.csv"
    write_excel(results, output_path)

    print(f"\n分析完成！共分析 {len(results)} 条创意")


def main():
    asyncio.run(analyze_ideas())


if __name__ == '__main__':
    main()
