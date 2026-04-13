import asyncio
import random
import re
import time
from typing import List, Dict, Optional, Tuple

from playwright.async_api import Page

from .config import (
    BASE_URL, SEARCH_URL, MAX_NOTES_PER_KEYWORD,
    COMMENT_SCROLL_PAUSE, MAX_CONCURRENT_PAGES,
    NOTE_DELAY_MIN, NOTE_DELAY_MAX, BATCH_DELAY
)
from .browser import BrowserManager
from .storage import Storage
from .ai_analyzer import AIAnalyzer


class XiaohongshuCrawler:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.browser = BrowserManager()

    async def start(self):
        await self.browser.start()

    async def close(self):
        await self.browser.close()

    async def crawl_keyword(self, keyword: str) -> List[Dict]:
        """Crawl top notes for a keyword."""
        keyword_id = self.storage.add_keyword(keyword)

        # Navigate to search results
        page = await self.browser.new_page()
        try:
            # Use type=51 for mobile-friendly search results
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=51"
            # Use 'commit' to avoid timeout on heavy JS pages
            await page.goto(search_url, wait_until='commit', timeout=30000)
            # Check for CAPTCHA and wait if needed
            await self.browser.wait_for_captcha_if_needed(page, timeout=120)
            # Wait for dynamic content to load
            await asyncio.sleep(3)

            # Try scrolling and waiting multiple times for JS content
            for attempt in range(10):
                try:
                    # Wait for any element that might indicate search results
                    await page.wait_for_selector('.feeds, .note-item, [class*="note"], .search-result', timeout=3000)
                    print(f"Search content found on attempt {attempt + 1}")
                    break
                except Exception:
                    print(f"Attempt {attempt + 1}: waiting more...")
                    # Scroll to trigger lazy load
                    await page.evaluate('window.scrollBy(0, 500)')
                    await asyncio.sleep(2)

            # Try multiple selectors for note items
            # Note: /search_result/ URLs have xsec_token and work; /explore/ URLs return 404
            selectors = [
                '.feeds-page a[href*="/search_result/"]',
                '.search-layout a[href*="/search_result/"]',
                'a[href*="/search_result/"]',
                '.feeds-page a[href*="/explore/"]',
                '.search-layout a[href*="/explore/"]',
                '.feeds a[href*="/explore/"]',
                'a[href*="/explore/"]',
            ]

            note_urls = []
            used_selector = None
            for selector in selectors:
                try:
                    # First check if any elements match
                    count = await page.evaluate(f'''(selector) => document.querySelectorAll(selector).length''', selector)
                    print(f"DEBUG: selector '{selector}' matches {count} elements")
                    if count > 0:
                        note_urls = await self._extract_note_urls(page, MAX_NOTES_PER_KEYWORD, selector)
                        if note_urls:
                            print(f"Found {len(note_urls)} notes using selector: {selector}")
                            used_selector = selector
                            break
                except Exception as e:
                    print(f"DEBUG: selector '{selector}' error: {e}")
                    continue

            if not note_urls:
                # Debug: find links in feeds-page
                links_info = await page.evaluate('''
                    () => {
                        const feedsPage = document.querySelector('.feeds-page');
                        if (!feedsPage) return {error: 'feeds-page not found'};
                        const links = feedsPage.querySelectorAll('a');
                        const linkInfo = [];
                        links.forEach((link, i) => {
                            if (i < 20) {
                                linkInfo.push({
                                    href: link.href,
                                    text: link.innerText.substring(0, 50)
                                });
                            }
                        });
                        return {
                            totalLinks: links.length,
                            links: linkInfo
                        };
                    }
                ''')
                print(f"Links in feeds-page: {links_info}")
                return []

            # Parallel crawl of notes
            notes_data = await self._crawl_notes_parallel(note_urls)

            # Initialize AI analyzer for comment cleaning
            ai_analyzer = AIAnalyzer(self.storage)
            all_cleaned_comments = []

            # Save to database and clean comments with AI
            for note_data in notes_data:
                self.storage.add_note(
                    keyword_id=keyword_id,
                    note_id=note_data['note_id'],
                    title=note_data['title'],
                    content=note_data['content'],
                    author=note_data['author'],
                    published_at=note_data['published_at'],
                    comment_count=note_data['comment_count']
                )
                new_count = self.storage.add_comments(note_data['note_id'], note_data['comments'])
                print(f"  Added {new_count} new comments for note: {note_data['title'][:30]}")

                # Send comments to AI for cleaning (every 50+ comments)
                if len(note_data['comments']) >= 10:
                    print(f"  Sending {len(note_data['comments'])} comments to AI for cleaning...")
                    cleaned = ai_analyzer.clean_comments_batch(note_data['comments'])
                    for c in cleaned:
                        c['note_id'] = note_data['note_id']
                        c['note_title'] = note_data['title']
                    all_cleaned_comments.extend(cleaned)
                    print(f"  AI returned {len(cleaned)} cleaned results")

            # Export cleaned comments to CSV
            if all_cleaned_comments:
                csv_path = self.storage.export_comments_to_csv(keyword, all_cleaned_comments)
                print(f"  Exported cleaned comments to {csv_path}")

            self.storage.update_keyword_crawled(keyword)
            return notes_data

        finally:
            await self.browser.close_page(page)

    async def _extract_note_urls(self, page: Page, limit: int, selector: str = '.note-item') -> List[str]:
        """Extract note URLs from search result page."""
        urls = []
        seen_urls = set()
        for _ in range(10):  # Try scrolling a few times
            # If selector is already an anchor or contains ' a', use it directly
            if selector.startswith('a[') or ' a[' in selector:
                url_elements = await page.query_selector_all(selector)
            else:
                url_elements = await page.query_selector_all(f'{selector} a')

            print(f"DEBUG: selector='{selector}', found {len(url_elements)} elements")

            for elem in url_elements:
                href = await elem.get_attribute('href')
                # Keep original URLs - both /explore/ and /search_result/ formats work
                if href and ('/explore/' in href or '/search_result/' in href):
                    full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        urls.append(full_url)

            if len(urls) >= limit:
                break
            # Scroll down to load more
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)

        print(f"DEBUG: extracted {len(urls)} URLs")
        return urls[:limit]

    async def _crawl_notes_parallel(self, urls: List[str]) -> List[Dict]:
        """Crawl multiple notes in parallel."""
        notes_data = []

        for i in range(0, len(urls), MAX_CONCURRENT_PAGES):  # Process MAX_CONCURRENT_PAGES at a time
            batch = urls[i:i+MAX_CONCURRENT_PAGES]
            pages = []
            for url in batch:
                page = await self.browser.new_page()
                pages.append((url, page))

            # Navigate with retries
            successful_pages = []
            for url, page in pages:
                for attempt in range(3):
                    try:
                        await page.goto(url, wait_until='commit', timeout=30000)
                        # Check for CAPTCHA and wait if needed
                        await self.browser.wait_for_captcha_if_needed(page, timeout=120)
                        successful_pages.append((url, page))
                        break
                    except Exception as e:
                        if attempt < 2:
                            await asyncio.sleep(5)
                        else:
                            await self.browser.close_page(page)

            # Wait for content to load
            await asyncio.sleep(3)

            # Crawl each page
            batch_results = []
            for url, page in successful_pages:
                try:
                    note_data = await self._crawl_single_note(page)
                    if note_data:
                        batch_results.append(note_data)
                except Exception as e:
                    print(f"Error crawling note {url}: {e}")
                finally:
                    await self.browser.close_page(page)

            notes_data.extend(batch_results)

            # Delay between batches to avoid rate limiting
            if i + MAX_CONCURRENT_PAGES < len(urls):
                print(f"  Waiting {BATCH_DELAY}s before next batch...")
                await asyncio.sleep(BATCH_DELAY)

        return notes_data

    async def _crawl_single_note(self, page: Page) -> Optional[Dict]:
        """Crawl a single note's full content and comments."""
        try:
            # Extract note metadata
            note_id = await self._extract_note_id(page)
            if not note_id:
                return None

            title = await self._extract_title(page)
            content = await self._extract_content(page)
            author = await self._extract_author(page)
            published_at = await self._extract_published_at(page)
            comment_count = await self._extract_comment_count(page)

            # Scroll to load all comments
            comments = await self._scroll_and_load_comments(page)

            return {
                'note_id': note_id,
                'title': title,
                'content': content,
                'author': author,
                'published_at': published_at,
                'comment_count': comment_count,
                'comments': comments
            }
        except Exception as e:
            print(f"Error in _crawl_single_note: {e}")
            return None

    async def _extract_note_id(self, page: Page) -> Optional[str]:
        """Extract note ID from page URL or page data."""
        url = page.url
        # Try /discovery/item/ format first
        match = re.search(r'/discovery/item/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        # Try /explore/ format
        match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        # Try /search_result/ format (has note ID before xsec_token)
        match = re.search(r'/search_result/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)

        # Fallback: try to get from page script data
        try:
            note_id = await page.evaluate('''
                () => {
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const match = script.textContent.match(/"noteId"\s*:\s*"([^"]+)"/);
                        if (match) return match[1];
                    }
                    return null;
                }
            ''')
            return note_id
        except Exception:
            return None

    async def _extract_title(self, page: Page) -> str:
        """Extract note title."""
        title = await page.evaluate('''
            () => {
                const el = document.querySelector('.note-content .title');
                return el ? el.textContent.trim() : '';
            }
        ''')
        if not title:
            title = await page.title()
        return title

    async def _extract_content(self, page: Page) -> str:
        """Extract note content."""
        content = await page.evaluate('''
            () => {
                const el = document.querySelector('.note-content .desc');
                return el ? el.textContent.trim() : '';
            }
        ''')
        return content

    async def _extract_author(self, page: Page) -> str:
        """Extract author name."""
        author = await page.evaluate('''
            () => {
                const el = document.querySelector('.author-wrapper .name');
                return el ? el.textContent.trim() : '';
            }
        ''')
        return author

    async def _extract_published_at(self, page: Page) -> str:
        """Extract publish time."""
        published_at = await page.evaluate('''
            () => {
                const el = document.querySelector('.publish-time');
                return el ? el.textContent.trim() : '';
            }
        ''')
        return published_at

    async def _extract_comment_count(self, page: Page) -> int:
        """Extract comment count."""
        count = await page.evaluate('''
            () => {
                const el = document.querySelector('.comment-count');
                if (!el) return 0;
                const match = el.textContent.match(/(\\d+)/);
                return match ? parseInt(match[1]) : 0;
            }
        ''')
        return count

    async def _scroll_and_load_comments(self, page: Page) -> List[Dict]:
        """Scroll to load all comments and extract them.

        Uses container-first scrolling with fallback to mouse wheel,
        mimicking human behavior to avoid detection.
        """
        comments = []
        last_count = 0
        no_new_count = 0
        scroller_selectors = [".note-scroller", ".interaction-container"]

        for scroll_attempt in range(30):  # Max 30 iterations
            try:
                # 先提取当前可见的评论
                new_comments = await self._extract_comments_from_page(page)
                for c in new_comments:
                    if c['id'] not in [existing['id'] for existing in comments]:
                        comments.append(c)

                current_count = len(comments)

                # 如果没有新评论，连续3次说明加载完了
                if current_count == last_count:
                    no_new_count += 1
                    if no_new_count >= 3:
                        break
                else:
                    last_count = current_count
                    no_new_count = 0

                # 滚动触发懒加载
                scroll_px = random.randint(200, 400)
                scrolled = False

                # Try container selectors first
                for sel in scroller_selectors:
                    scroller = await page.query_selector(sel)
                    if scroller:
                        await scroller.evaluate(f"el => el.scrollBy(0, {scroll_px})")
                        scrolled = True
                        break

                # Fallback to mouse wheel
                if not scrolled:
                    await page.mouse.wheel(0, scroll_px)

                # Wait: fixed delay + random delay (mimics human behavior)
                await asyncio.sleep(COMMENT_SCROLL_PAUSE)
                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                # 如果有错误（如页面导航），停止滚动
                break

        # 最终提取
        try:
            final_comments = await self._extract_comments_from_page(page)
            for c in final_comments:
                if c['id'] not in [existing['id'] for existing in comments]:
                    comments.append(c)
        except Exception:
            pass

        return comments

    async def _extract_comments_from_page(self, page: Page) -> List[Dict]:
        """Extract comment elements from current page view."""
        comments = await page.evaluate('''
            () => {
                const items = document.querySelectorAll('.comment-item');
                return Array.from(items).map(item => {
                    // Extract comment ID from item.id (format: "comment-xxxxx")
                    const idMatch = item.id.match(/comment-(.+)/);
                    const id = idMatch ? idMatch[1] : item.id || Math.random().toString(36);
                    const userEl = item.querySelector('.name');
                    const contentEl = item.querySelector('.content');
                    const likeEl = item.querySelector('.like');
                    const timeEl = item.querySelector('.time');
                    return {
                        id: id,
                        user: userEl ? userEl.textContent.trim() : '',
                        content: contentEl ? contentEl.textContent.trim() : '',
                        like_count: likeEl ? parseInt(likeEl.textContent) || 0 : 0,
                        created_at: timeEl ? timeEl.textContent.trim() : ''
                    };
                });
            }
        ''')
        return comments


# Synchronous wrapper
def crawl_keyword_sync(keyword: str, storage: Storage) -> List[Dict]:
    """Synchronous wrapper for crawl_keyword."""
    crawler = XiaohongshuCrawler(storage)

    async def run():
        await crawler.start()
        try:
            return await crawler.crawl_keyword(keyword)
        finally:
            await crawler.close()

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(run())
    loop.close()
    return result
