import asyncio
import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, urljoin, urldefrag

import aiohttp  # Add this import at the top
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.crawler.browser_pool import BrowserPool
from src.crawler.frontier import PriorityFrontier
from src.etl import ETL
from src.storage.bloom_filter import VisitedURLTracker
from src.storage.postgres import AsyncPostgres
from src.utils.metrics import CrawlerMetrics
from src.utils.rate_limiter import DomainRateLimiter

load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)


class WebScraper:
    def __init__(self):
        self.browser_pool = BrowserPool(max_instances=20)
        self.visited = VisitedURLTracker()
        self.frontier = PriorityFrontier()
        self.rate_limiter = DomainRateLimiter(base_delay=1.0)
        self.db = AsyncPostgres()
        self.metrics = CrawlerMetrics()
        self.current_batch = []
        self.BATCH_SIZE = 10
        self.executor = ProcessPoolExecutor()  # For CPU-bound tasks
        self.semaphore = asyncio.Semaphore(100)  # Concurrent request limit

    async def initialize(self):
        """Async initialization with validation"""
        db_config = {
            "user": os.getenv("DATABASE_USER"),
            "password": os.getenv("DATABASE_PASSWORD"),
            "host": os.getenv("DATABASE_HOST"),
            "port": os.getenv("DATABASE_PORT"),
            "database": os.getenv("DATABASE_NAME")
        }
        await self.db.connect(db_config)

        # Initialize ETL and create table
        self.etl = ETL(self.db)
        await self.etl.initialize()  # <-- This now creates the table

        # Validate connection pool
        if not self.db.pool:
            raise RuntimeError("Database connection failed")

    async def crawl_websites(self, domains: list) -> list:
        """Entry point for crawling multiple domains"""
        try:
            for domain in domains:
                self.frontier.add_url(domain)

            while not self.frontier.empty():
                url = self.frontier.get_next()

                if await self._should_skip(url):
                    continue

                await self._process_url(url)

                if len(self.current_batch) >= self.BATCH_SIZE:
                    await self._flush_batch()

            # Flush remaining URLs
            if self.current_batch:
                await self._flush_batch()

            return self.metrics.report()

        finally:
            await self._cleanup_resources()

    async def _should_skip(self, url: str) -> bool:
        """Decision logic for URL processing"""
        if url in self.visited:
            return True

        parsed = urlparse(url)
        if not parsed.netloc or not parsed.scheme:
            return True

        return False

    async def _process_url(self, url: str):
        """Core URL processing pipeline"""
        domain = urlparse(url).netloc
        self.visited.add(url)

        try:
            await self.rate_limiter.throttle(domain)
            content = await self._fetch_content(url)

            if content:
                is_product = self._analyze_content(url, content)
                await self._handle_links(content, url, is_product)

                if is_product:
                    self._add_to_batch(url, domain)
                    self.metrics.update(product_urls=1)

                self.metrics.update(urls_crawled=1)

        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)[:200]}")
            self.metrics.update(errors=1)

    async def _fetch_content(self, url: str) -> str:
        """Hybrid content fetching with smart retries"""
        for attempt in range(3):
            try:
                if self._requires_js(url):
                    return await self._fetch_with_browser(url)
                return await self._fetch_http(url)
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                await asyncio.sleep(2 ** attempt)
        return None

    def _requires_js(self, url: str) -> bool:
        """Heuristic for JS requirement detection"""
        return any(indicator in url for indicator in
                   ['/react/', '/vue/', '/angular/', 'single-page-app'])

    async def _fetch_http(self, url: str) -> str:
        """Lightweight HTTP fetcher"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()

    async def _fetch_with_browser(self, url: str) -> str:
        """Browser-based fetcher with resource pooling"""
        print("_fetch_with_browser")
        browser = await self.browser_pool.acquire()
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            content = await page.content()
            return content
        finally:
            await page.close()
            await self.browser_pool.release(browser)

    def _analyze_content(self, url: str, content: str) -> bool:
        """Determine if URL is a product page"""
        # Fast path check first
        if self._is_product_url(url):
            return True

    def _is_product_url(self, url: str) -> bool:
        """Determine if URL points to a product page (optimized for Indian e-commerce sites)"""
        product_patterns = [
            # Myntra/Ajio/Nykaa: /p/<alphanum> or /buy
            r"/p/[\w-]+", r"/buy/?$",
            # Flipkart/Amazon: /dp/, /gp/product/, or pid=
            r"/dp/[\w]{10}", r"/gp/product/[\w]{10}", r"[&?]pid=[\d\w]+",
            # Tata CLiQ: /p-mp<digits> or /p-
            r"/p-[\w]+", r"/p-mp\d+",
            # Limeroad: -p followed by digits (e.g., showoff-p21597399)
            r"-p\d+",
            # Bewakoof: /p/ followed by descriptive slug
            r"/p/[\w-]+",
            # Numeric product ID in path (e.g., Myntra's 31340477)
            r"/\d{6,}/"
        ]

        excluded_patterns = [
            r"/category/", r"/search", r"\.(jpg|png|webp)(\?|$)",
            r"/cart", r"/checkout", r"/review", r"/wishlist",
            r"/store/", r"/shop/", r"/list/", r"/filter", r"/login", r"/product-reviews", r"/auth"
        ]

        url_lower = url.lower()

        # Check for product patterns and exclusions
        is_product = (
                any(re.search(p, url_lower) for p in product_patterns) and
                not any(re.search(e, url_lower) for e in excluded_patterns)
        )

        # Additional validation for product IDs
        has_product_id = (
                re.search(r"\b\d{6,}\b", url) or  # Numeric ID (Myntra)
                re.search(r"[_-][a-z0-9]{8,}", url_lower)  # Alphanumeric ID (Ajio/Limeroad)
        )

        return is_product and has_product_id

    async def _handle_links(self, content: str, base_url: str, is_product: bool):
        """Link extraction and frontier management"""
        soup = BeautifulSoup(content, 'lxml')
        for link in soup.find_all('a', href=True):
            try:
                full_url = urljoin(base_url, link['href'])
                full_url = urldefrag(full_url).url

                if not self._should_crawl(full_url, base_url):
                    continue

                self.frontier.add_url(full_url)

            except Exception as e:
                logging.debug(f"Link processing error: {str(e)[:50]}")

    def _should_crawl(self, url: str, base_url: str) -> bool:
        """Crawl policy decision"""
        parsed = urlparse(url)
        base_domain = urlparse(base_url).netloc

        return (
                parsed.netloc == base_domain and
                parsed.path not in ['/search', '/filter'] and
                not parsed.query.startswith('utm_') and
                not re.search(r'\.(css|js|png|jpg)$', url)
        )

    def _add_to_batch(self, url: str, domain: str):
        """Batch management for bulk inserts"""
        self.current_batch.append((url, domain))
        if len(self.current_batch) >= self.BATCH_SIZE:
            asyncio.create_task(self._flush_batch())

    async def _flush_batch(self):
        """Database batch insert operation with safety checks"""
        if not self.db or not self.db.pool:
            logging.error("Database connection not initialized")
            return

        try:
            await self.db.bulk_insert_urls(self.current_batch)
            self.metrics.update(batches_flushed=1)
            self.current_batch = []
        except Exception as e:
            logging.error(f"Batch insert failed: {str(e)[:200]}")
            self.metrics.update(db_errors=1)

    async def _cleanup_resources(self):
        """Graceful resource cleanup"""
        if self.db:
            await self.db.close()
        if self.browser_pool:
            await self.browser_pool.shutdown()  # Now uses the proper shutdown
        logging.info("Crawler resources cleaned up")

    # scraper.py (WebScraper class)
    async def close(self):
        """Public cleanup method with guard clause"""
        if hasattr(self, '_closed') and self._closed:
            return
        await self._cleanup_resources()
        self._closed = True  # Mark as closed
