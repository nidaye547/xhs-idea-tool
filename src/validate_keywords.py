#!/usr/bin/env python3
"""验证关键词质量 - 检查搜索结果是否符合预期目的"""
import asyncio
import random
import re
import sys
import os
from pathlib import Path

# Force headless mode
os.environ['HEADLESS'] = 'true'

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.browser import BrowserManager
from src.config import BASE_URL

# 待验证的关键词列表
KEYWORDS = [
    "你们有没有突然发现一个需求然后做成的",
    "有没有什么生意是你无意中发现的",
    "说一个你自己真正赚过钱的事",
    "有没有人跟我一样 从什么都不懂开始做",
    "你们那些奇怪的客户都是哪来的",
    "有没有人发现某个需求但不知道怎么商业化",
    "你们第一笔赚钱是怎么来的",
    "有没有一种需求 你做了才发现很赚钱",
    "说说你们那些不起眼但赚钱的事",
    "有没有什么你们圈子知道但外面不知道的赚钱方式",
]


async def validate_keyword(browser: BrowserManager, keyword: str) -> dict:
    """验证单个关键词"""
    page = await browser.new_page()
    try:
        # 访问搜索页
        search_url = f"{BASE_URL}/search_result?keyword={keyword}&type=51"
        await page.goto(search_url, wait_until='commit', timeout=30000)

        # 等待验证码检查
        await browser.wait_for_captcha_if_needed(page, timeout=120)

        # 等待内容加载
        await asyncio.sleep(3)

        # 尝试滚动加载
        for _ in range(5):
            await page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(1)

        # 提取笔记标题
        titles = await page.evaluate('''
            () => {
                const selectors = [
                    '.feeds-page .note-item .title',
                    '.feeds-page .title',
                    '.note-item .title',
                    '[class*="title"]',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        return Array.from(els).slice(0, 10).map(el => el.textContent.trim()).filter(t => t);
                    }
                }
                return [];
            }
        ''')

        # 如果上面的方法不行，试试提取所有链接文本
        if not titles:
            titles = await page.evaluate('''
                () => {
                    const links = document.querySelectorAll('.feeds-page a[href*="/search_result/"], .feeds-page a[href*="/explore/"]');
                    return Array.from(links).slice(0, 10).map(l => l.textContent.trim()).filter(t => t && t.length > 5);
                }
            ''')

        await browser.close_page(page)
        return {
            'keyword': keyword,
            'titles': titles,
            'count': len(titles)
        }
    except Exception as e:
        await browser.close_page(page)
        return {
            'keyword': keyword,
            'titles': [],
            'count': 0,
            'error': str(e)
        }


async def main():
    browser = BrowserManager()
    await browser.start()

    results = []
    for i, keyword in enumerate(KEYWORDS, 1):
        print(f"[{i}/{len(KEYWORDS)}] 验证: {keyword}")
        result = await validate_keyword(browser, keyword)
        results.append(result)

        print(f"  获取到 {result['count']} 个标题:")
        for j, title in enumerate(result.get('titles', [])[:5], 1):
            print(f"    {j}. {title[:50]}...")

        # 间隔5+随机秒
        if i < len(KEYWORDS):
            delay = 5 + random.uniform(0, 5)
            print(f"  等待 {delay:.1f}s...")
            await asyncio.sleep(delay)

    await browser.close()

    # 输出结果表格
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)
    print(f"{'序号':<4} {'关键词':<30} {'标题数':<6} {'状态'}")
    print("-" * 80)

    for i, r in enumerate(results, 1):
        status = "✓ 有结果" if r['count'] > 0 else "✗ 无结果"
        if 'error' in r:
            status = f"✗ 错误: {r['error'][:30]}"
        print(f"{i:<4} {r['keyword'][:28]:<30} {r['count']:<6} {status}")

    # 保存详细结果
    import json
    output_path = Path(__file__).parent.parent / "output" / "keyword_validation.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == '__main__':
    asyncio.run(main())
