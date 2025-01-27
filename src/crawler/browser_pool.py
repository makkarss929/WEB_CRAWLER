# src/crawler/browser_pool.py
import asyncio
import logging
from playwright.async_api import async_playwright


class BrowserPool:
    def __init__(self, max_instances=5):
        self.max_instances = max_instances
        self.free_instances = []
        self.all_browsers = []
        self.playwright = None
        self.lock = asyncio.Lock()
        self.is_shutdown = False
        logging.basicConfig(level=logging.INFO)

    async def acquire(self):
        """Acquire a browser instance from the pool"""
        if self.is_shutdown or not self.playwright:
            raise RuntimeError("Browser pool is shutdown")

        async with self.lock:
            # Reuse existing instance if available
            if self.free_instances:
                return self.free_instances.pop()

            # Create new instance if under limit
            if len(self.all_browsers) < self.max_instances:
                if not self.playwright:
                    self.playwright = await async_playwright().start()

                browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage'
                    ],
                    timeout=60000
                )
                self.all_browsers.append(browser)
                logging.info(f"Created new browser instance (total: {len(self.all_browsers)})")
                return browser

            # Wait for free instance if at max capacity
            while not self.free_instances:
                await asyncio.sleep(0.1)
            return self.free_instances.pop()

    async def release(self, browser):
        """Return a browser instance to the pool"""
        async with self.lock:
            if not self.is_shutdown and len(self.free_instances) < self.max_instances:
                self.free_instances.append(browser)
            else:
                await browser.close()

    async def shutdown(self):
        """Cleanup all resources gracefully"""
        async with self.lock:
            if self.is_shutdown:
                return

            self.is_shutdown = True
            logging.info("Shutting down browser pool...")

            # Close all browsers
            for browser in self.all_browsers:
                try:
                    await browser.close()
                except Exception as e:
                    logging.error(f"Error closing browser: {str(e)}")

            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.free_instances.clear()
            self.all_browsers.clear()
            logging.info("Browser pool shutdown complete")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()