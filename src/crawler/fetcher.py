import aiohttp
from src.crawler.browser_pool import BrowserPool

class HybridFetcher:
    def __init__(self):
        self.browser_pool = BrowserPool()
        self.http_session = aiohttp.ClientSession()

    async def fetch(self, url):
        if self._needs_js(url):
            return await self._fetch_with_browser(url)
        return await self._fetch_http(url)

    async def _fetch_http(self, url):
        async with self.http_session.get(url) as response:
            return await response.text()

    async def _fetch_with_browser(self, url):
        browser = await self.browser_pool.acquire()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await page.close()
        await self.browser_pool.release(browser)
        return content

    def _needs_js(self, url):
        return any(d in url for d in ['react', 'vue', 'angular'])