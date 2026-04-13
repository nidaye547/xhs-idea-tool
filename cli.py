#!/usr/bin/env python3
"""小红书创意发现工具 - CLI 版本"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage import Storage
from src.crawler import XiaohongshuCrawler
from src.ai_analyzer import AIAnalyzer
from src.config import HEADLESS, AI_MODEL, AI_PROVIDER, OPENAI_BASE_URL


class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def color(text, c):
    """Colorize text"""
    return f"{c}{text}{Colors.ENDC}"


def print_banner():
    """Print banner"""
    banner = f"""
{color('╔═══════════════════════════════════════════════════╗', Colors.CYAN)}
{color('║       小红书创意发现工具 v1.0                     ║', Colors.CYANAN)}
{color('║       发现真实用户需求，激发内容灵感              ║', Colors.CYAN)}
{color('╚═══════════════════════════════════════════════════╝', Colors.CYAN)}
    """
    print(banner)


def load_config():
    """Load config from config.json"""
    config_path = PROJECT_ROOT / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config):
    """Save config to config.json"""
    config_path = PROJECT_ROOT / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def cmd_search(args):
    """Search for ideas"""
    config = load_config()

    # Check required config
    if not config.get('cookie'):
        print(color("错误: 请先配置 Cookie", Colors.RED))
        print(color("运行: xhs-cli config --cookie 'your_cookie'", Colors.YELLOW))
        sys.exit(1)

    keyword = args.keyword
    print(f"\n{color('🔍 搜索关键词:', Colors.BLUE)} {color(keyword, Colors.BOLD)}")
    print(color('─' * 50, Colors.DIM))

    storage = Storage()

    async def run():
        crawler = XiaohongshuCrawler(storage)

        # Set cookie
        os.environ['XHS_COOKIE'] = config['cookie']

        # Set proxy if configured
        if config.get('use_proxy') and config.get('proxy'):
            os.environ['HTTP_PROXY'] = config['proxy']
            os.environ['HTTPS_PROXY'] = config['proxy']
        else:
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                os.environ.pop(var, None)

        # Set headless
        if config.get('headless') is not None:
            os.environ['HEADLESS'] = 'true' if config['headless'] else 'false'

        await crawler.start()
        try:
            print(color("📡 正在获取笔记...", Colors.YELLOW))
            notes = await crawler.crawl_keyword(keyword)
            print(color(f"   找到 {len(notes)} 个笔记", Colors.GREEN))

            if not notes:
                print(color("   未找到任何笔记", Colors.YELLOW))
                return

            # Get comments
            print(color("💬 正在获取评论...", Colors.YELLOW))
            all_comments = []
            for note in notes:
                comments = storage.get_comments_for_note(note['note_id'])
                for c in comments:
                    c['note_id'] = note['note_id']
                    c['note_title'] = note.get('title', '')
                all_comments.extend(comments)
            print(color(f"   获取到 {len(all_comments)} 条评论", Colors.GREEN))

            if not all_comments:
                print(color("   没有评论数据", Colors.YELLOW))
                return

            # AI clean
            print(color("🤖 正在 AI 清洗...", Colors.YELLOW))
            analyzer = AIAnalyzer(storage)
            cleaned = analyzer.clean_comments_batch(all_comments)
            print(color(f"   清洗完成，获得 {len(cleaned)} 条创意", Colors.GREEN))

            if not cleaned:
                print(color("   没有有价值的创意", Colors.YELLOW))
                return

            # Display results
            print(f"\n{color('📊 创意列表:', Colors.GREEN)}")
            print(color('─' * 70, Colors.DIM))

            for i, item in enumerate(cleaned[:args.limit], 1):
                content = item.get('cleaned_view', item.get('original_content', ''))[:60]
                user = item.get('user', '匿名')
                score = item.get('feasibility_score', '-')
                note_title = item.get('note_title', '未知来源')[:15]

                score_color = Colors.GREEN if (isinstance(score, int) and score >= 4) else \
                              Colors.YELLOW if (isinstance(score, int) and score >= 3) else Colors.RED

                print(f"{i:2}. {color(content, Colors.BOLD)}")
                print(f"    {color('👤', Colors.DIM)}{user} | {color('⭐', score_color)}{score} | {color('📝', Colors.DIM)}{note_title}")

            print(color('─' * 70, Colors.DIM))
            print(f"{color('总计:', Colors.BLUE)} {len(cleaned)} 条创意")

            # Save to favorites
            if args.save:
                favorites_path = PROJECT_ROOT / "favorites.json"
                favorites = []
                if favorites_path.exists():
                    try:
                        with open(favorites_path, 'r', encoding='utf-8') as f:
                            favorites = json.load(f)
                    except:
                        favorites = []

                # Deduplicate
                existing_hashes = set(hash(f.get('cleaned_view', '')) for f in favorites)
                new_count = 0
                for item in cleaned:
                    h = hash(item.get('cleaned_view', ''))
                    if h not in existing_hashes:
                        favorites.append(item)
                        existing_hashes.add(h)
                        new_count += 1

                with open(favorites_path, 'w', encoding='utf-8') as f:
                    json.dump(favorites, f, ensure_ascii=False, indent=2)

                print(f"\n{color('💾 已保存 {new_count} 条新创意到收藏夹', Colors.GREEN)}")

        finally:
            await crawler.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


def cmd_favorites(args):
    """Show favorites"""
    favorites_path = PROJECT_ROOT / "favorites.json"

    if not favorites_path.exists():
        print(color("收藏夹是空的", Colors.YELLOW))
        return

    try:
        with open(favorites_path, 'r', encoding='utf-8') as f:
            favorites = json.load(f)
    except:
        print(color("读取收藏夹失败", Colors.RED))
        favorites = []

    if not favorites:
        print(color("收藏夹是空的", Colors.YELLOW))
        return

    print(f"\n{color('⭐ 我的收藏夹:', Colors.GREEN)} ({len(favorites)} 条)")
    print(color('─' * 70, Colors.DIM))

    for i, item in enumerate(favorites[:args.limit], 1):
        content = item.get('cleaned_view', '')[:60]
        user = item.get('user', '匿名')
        score = item.get('feasibility_score', '-')
        note_title = item.get('note_title', '未知来源')[:15]
        note_id = item.get('note_id', '')

        score_color = Colors.GREEN if (isinstance(score, int) and score >= 4) else \
                      Colors.YELLOW if (isinstance(score, int) and score >= 3) else Colors.RED

        url = f"https://www.xiaohongshu.com/discovery/item/{note_id}" if note_id else ""

        print(f"{i:2}. {color(content, Colors.BOLD)}")
        print(f"    {color('👤', Colors.DIM)}{user} | {color('⭐', score_color)}{score} | {color('📝', Colors.DIM)}{note_title}")
        if url:
            print(f"    {color('🔗', Colors.DIM)}{url}")


def cmd_config(args):
    """Configure settings"""
    config = load_config()

    if args.show:
        print(f"\n{color('⚙️  当前配置:', Colors.BLUE)}")
        print(color('─' * 40, Colors.DIM))
        sensitive = ['api_key', 'cookie']
        for key, value in config.items():
            if key in sensitive and value:
                display = value[:10] + '...' if len(str(value)) > 10 else value
            else:
                display = value if value else '(未设置)'
            print(f"  {key}: {display}")

    if args.api_key:
        config['api_key'] = args.api_key
        print(color(f"✓ API Key 已设置", Colors.GREEN))

    if args.model:
        config['model'] = args.model
        print(color(f"✓ 模型已设置为: {args.model}", Colors.GREEN))

    if args.base_url:
        config['base_url'] = args.base_url
        print(color(f"✓ Base URL 已设置为: {args.base_url}", Colors.GREEN))

    if args.cookie:
        config['cookie'] = args.cookie
        print(color("✓ Cookie 已设置", Colors.GREEN))

    if args.proxy:
        config['proxy'] = args.proxy
        print(color(f"✓ 代理已设置为: {args.proxy}", Colors.GREEN))

    if args.headless is not None:
        config['headless'] = args.headless
        mode = "无头模式" if args.headless else "显示浏览器"
        print(color(f"✓ 浏览器模式: {mode}", Colors.GREEN))

    if args.api_key or args.model or args.base_url or args.cookie or args.proxy or args.headless is not None:
        save_config(config)
        print(color(f"\n✓ 配置已保存到 config.json", Colors.GREEN))


def cmd_export(args):
    """Export favorites to CSV"""
    favorites_path = PROJECT_ROOT / "favorites.json"

    if not favorites_path.exists():
        print(color("收藏夹是空的", Colors.YELLOW))
        return

    try:
        with open(favorites_path, 'r', encoding='utf-8') as f:
            favorites = json.load(f)
    except:
        print(color("读取收藏夹失败", Colors.RED))
        return

    if not favorites:
        print(color("收藏夹是空的", Colors.YELLOW))
        return

    import csv
    output_path = args.output or f"favorites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['创意内容', '用户', '点赞', '可行性', '来源笔记', '笔记链接'])
        for item in favorites:
            note_id = item.get('note_id', '')
            url = f"https://www.xiaohongshu.com/discovery/item/{note_id}" if note_id else ''
            writer.writerow([
                item.get('cleaned_view', ''),
                item.get('user', ''),
                item.get('like_count', 0),
                item.get('feasibility_score', ''),
                item.get('note_title', ''),
                url
            ])

    print(color(f"✓ 已导出到 {output_path}", Colors.GREEN))


def main():
    parser = argparse.ArgumentParser(
        description='小红书创意发现工具 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # Search command
    search_parser = subparsers.add_parser('search', help='搜索关键词')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--limit', '-n', type=int, default=20, help='显示数量 (默认20)')
    search_parser.add_argument('--save', '-s', action='store_true', help='保存到收藏夹')

    # Favorites command
    favorites_parser = subparsers.add_parser('favorites', aliases=['fav'], help='显示收藏夹')
    favorites_parser.add_argument('--limit', '-n', type=int, default=50, help='显示数量 (默认50)')

    # Config command
    config_parser = subparsers.add_parser('config', help='配置设置')
    config_parser.add_argument('--show', '-s', action='store_true', help='显示当前配置')
    config_parser.add_argument('--api-key', help='设置 API Key')
    config_parser.add_argument('--model', help='设置模型 (如 gpt-4o-mini)')
    config_parser.add_argument('--base-url', help='设置 API Base URL')
    config_parser.add_argument('--cookie', help='设置小红书 Cookie')
    config_parser.add_argument('--proxy', help='设置代理 (如 http://127.0.0.1:7890)')
    config_parser.add_argument('--headless', type=lambda x: x.lower() == 'true',
                               help='设置无头模式 (true/false)')

    # Export command
    export_parser = subparsers.add_parser('export', help='导出收藏夹')
    export_parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    print_banner()

    if args.command == 'search':
        cmd_search(args)
    elif args.command == 'favorites' or args.command == 'fav':
        cmd_favorites(args)
    elif args.command == 'config':
        cmd_config(args)
    elif args.command == 'export':
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
