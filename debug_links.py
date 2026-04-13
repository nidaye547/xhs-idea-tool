import asyncio
import sys
sys.path.insert(0, '/app/src')
from browser import BrowserManager

async def test():
    browser = BrowserManager()
    await browser.start()

    page = await browser.new_page()

    await page.goto('https://www.xiaohongshu.com/search_result?keyword=app&type=51', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(5)

    # Get ALL links on the page
    all_links = await page.evaluate('''() => {
        const links = document.querySelectorAll('a');
        const seen = new Set();
        const result = [];
        links.forEach(l => {
            const href = l.href;
            if (href && !seen.has(href) && href.includes('xiaohongshu')) {
                seen.add(href);
                if (result.length < 20) {
                    result.push({
                        href: href,
                        text: l.innerText.substring(0, 50)
                    });
                }
            }
        });
        return result;
    }''')

    print('All xiaohongshu links:')
    for link in all_links:
        href = link['href']
        text = link['text']
        print(f'  {href}')
        print(f'    Text: {text[:80]}')

    await browser.close()

asyncio.run(test())