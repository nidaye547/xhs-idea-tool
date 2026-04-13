import asyncio
import os
import random
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from .config import HEADLESS, MAX_CONCURRENT_PAGES

# Try importing stealth libraries, gracefully degrade if not available
try:
    import playwright_stealth as stealth_module
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

try:
    from browserforge.fingerprints import Browser as FpBrowser
    from browserforge.fingerprints import Fingerprint
    FINGERPRINT_AVAILABLE = True
except ImportError:
    FINGERPRINT_AVAILABLE = False


class BrowserManager:
    _instance: Optional['BrowserManager'] = None
    _playwright = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _generate_fingerprint(self) -> dict:
        """Generate a random browser fingerprint."""
        if FINGERPRINT_AVAILABLE:
            try:
                fp = FpBrowser.Chrome.generate()
                return {
                    'user_agent': fp.navigator.userAgent,
                    'viewport': {'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
                    'screen_width': fp.navigator.screenWidth or 1920,
                    'screen_height': fp.navigator.screenHeight or 1080,
                }
            except Exception:
                pass

        # Fallback: random user agent
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        ]
        return {
            'user_agent': random.choice(user_agents),
            'viewport': {'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
            'screen_width': 1920,
            'screen_height': 1080,
        }

    async def start(self):
        if self._browser is not None:
            return

        self._playwright = await async_playwright().start()

        # Generate fingerprint
        fp = self._generate_fingerprint()

        # Choose browser: Chrome if not headless, Firefox if headless (chromium crashes on macOS)
        if HEADLESS:
            # Use Firefox for headless mode (chromium crashes)
            self._browser = await self._playwright.firefox.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-gpu',
                ]
            )
        else:
            # Use system Chrome for non-headless mode
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                channel='chrome',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-sync',
                    '--disable-site-isolation-trials',
                    '--disable-web-security',
                    '--js-flags=--max-old-space-size=4096',
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches-enable-automation',
                    '--disable-infobars',
                ]
            )

        self._context = await self._browser.new_context(
            viewport=fp['viewport'],
            user_agent=fp['user_agent'],
        )

        # Apply stealth patches if available (done per-page in new_page())
        if STEALTH_AVAILABLE:
            pass  # stealth applied in new_page()

        # Set cookie from environment if provided
        cookie_str = os.getenv('XHS_COOKIE', '')
        if cookie_str:
            cookies = self._parse_cookie_string(cookie_str)
            if cookies:
                await self._context.add_cookies(cookies)
                print(f"Added {len(cookies)} cookies for Xiaohongshu")

    def _parse_cookie_string(self, cookie_str: str) -> List[dict]:
        """Parse cookie string into list of cookie dicts for Playwright."""
        cookies = []
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.xiaohongshu.com',
                    'path': '/',
                })
        return cookies

    async def wait_for_captcha_if_needed(self, page: Page, timeout: int = 300) -> bool:
        """Check if CAPTCHA is present and wait for manual resolution.

        Returns True if CAPTCHA was detected and user resolved it.
        Returns False if no CAPTCHA was detected.
        Raises TimeoutError if CAPTCHA is not resolved within timeout seconds.
        """
        max_wait = timeout
        check_interval = 2

        while max_wait > 0:
            try:
                # Check if we're on a CAPTCHA page
                url = page.url
                title = await page.title()

                if 'captcha' in url.lower() or 'captcha' in title.lower() or 'Security Verification' in title:
                    print(f"CAPTCHA detected! URL: {url}")
                    print("Please complete the verification in the browser window.")
                    print(f"Waiting up to {max_wait} seconds for resolution...")

                    # Wait and check again
                    await asyncio.sleep(check_interval)
                    max_wait -= check_interval

                    # Check if still on CAPTCHA
                    try:
                        new_url = page.url
                        new_title = await page.title()
                        if 'captcha' not in new_url.lower() and 'captcha' not in new_title.lower() and 'Security Verification' not in new_title:
                            print("CAPTCHA resolved!")
                            return True
                    except Exception:
                        pass
                else:
                    # No CAPTCHA detected
                    return False

            except Exception as e:
                print(f"Error checking CAPTCHA status: {e}")
                await asyncio.sleep(check_interval)
                max_wait -= check_interval

        print("CAPTCHA wait timeout!")
        return False

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def new_page(self) -> Page:
        if self._context is None:
            await self.start()
        page = await self._context.new_page()

        # Apply stealth to page (disabled for now)
        # if STEALTH_AVAILABLE:
        #     await stealth_module.stealth(page)
        pass

        return page

    async def goto_with_captcha_check(self, url: str, wait_until: str = 'commit', timeout: int = 30000) -> Page:
        """Navigate to URL and wait for CAPTCHA resolution if needed."""
        page = await self.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout)

        # Check for CAPTCHA and wait if needed
        await self.wait_for_captcha_if_needed(page, timeout=120)

        return page

        return page

    async def close_page(self, page: Page):
        await page.close()

    async def batch_pages(self, urls: List[str]) -> List[Page]:
        """Open multiple pages in parallel, up to MAX_CONCURRENT_PAGES."""
        pages = []
        for i in range(0, len(urls), MAX_CONCURRENT_PAGES):
            batch = urls[i:i + MAX_CONCURRENT_PAGES]
            batch_pages = [await self.new_page() for _ in batch]
            tasks = [page.goto(url, wait_until='domcontentloaded') for page in batch_pages]
            await asyncio.gather(*tasks)
            pages.extend(batch_pages)
        return pages[:len(urls)]


# Synchronous wrapper for easier use
class SyncBrowserManager:
    def __init__(self):
        self._async_manager = BrowserManager()
        self._loop = None

    def _ensure_loop(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()

    def start(self):
        self._ensure_loop()
        self._loop.run_until_complete(self._async_manager.start())

    def close(self):
        if self._loop:
            self._loop.run_until_complete(self._async_manager.close())

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    async def _new_page(self) -> Page:
        return await self._async_manager.new_page()

    async def _close_page(self, page: Page):
        await self._async_manager.close_page(page)

    async def _batch_pages(self, urls: List[str]) -> List[Page]:
        return await self._async_manager.batch_pages(urls)

    def new_page(self) -> Page:
        return self._loop.run_until_complete(self._new_page())

    def close_page(self, page: Page):
        self._loop.run_until_complete(self._close_page(page))

    def batch_pages(self, urls: List[str]) -> List[Page]:
        return self._loop.run_until_complete(self._batch_pages(urls))
