import asyncio
import logging
import random
import re
from urllib.parse import urljoin, urldefrag
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from src.etl import ETL

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
    def __init__(self) -> None:
        self.etl = ETL()
        self.playwright = None
        self.browser = None
        self.context = None
        self.max_retries = 3
        self.delay_range = (1, 3)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15"
        ]
        self._active_pages = set()
        self._browser_lock = asyncio.Lock()

    async def init_browser(self):
        """Initialize browser instance with proper resource management"""
        async with self._browser_lock:
            if not self.playwright:
                self.playwright = await async_playwright().start()

            if not self.browser or not self.browser.is_connected():
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage'
                    ],
                    timeout=60000
                )

            # Create new context if needed
            if not self.context or self.context.browser.is_connected():
                if self.context:
                    await self.context.close()
                self.context = await self.browser.new_context(
                    user_agent=random.choice(self.user_agents),
                    viewport={'width': 1920, 'height': 1080}
                )

    async def fetch_page(self, url: str) -> str:
        """Robust page fetching with proper error handling"""
        for attempt in range(self.max_retries):
            page = None
            try:
                await self.init_browser()
                page = await self.context.new_page()

                # Configure stealth plugins
                await stealth_async(page)
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                # Set up request interception
                await page.route('**/*', self._handle_route)

                # Navigate with timeout scaling
                await page.goto(
                    url,
                    timeout=30000 + (10000 * attempt),
                    wait_until="domcontentloaded"
                )

                # Wait for core content
                await self._wait_for_content(page, attempt)

                # Get and validate content
                content = await page.content()
                if self._is_valid_content(content):
                    return content

                raise Exception("Content validation failed")

            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)[:80]}")
                if attempt == self.max_retries - 1:
                    raise
                await self._perform_cleanup(page)
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            finally:
                await self._close_page(page)

        return ""

    async def _handle_route(self, route):
        """Route handler for blocking unnecessary resources"""
        if route.request.resource_type in ['image', 'stylesheet', 'font']:
            await route.abort()
        else:
            await route.continue_()

    async def _wait_for_content(self, page, attempt):
        """Intelligent content waiting strategy"""
        try:
            # Wait for body element as basic validation
            await page.wait_for_selector('body', state='attached',
                                         timeout=15000 + (5000 * attempt))

            # Additional content length check
            content = await page.content()
            if len(content) < 1024:
                raise Exception("Insufficient content length")
        except Exception as e:
            logging.warning(f"Content wait failed: {str(e)}")
            raise

    def _is_valid_content(self, content):
        """Basic content validation checks"""
        return any([
            '<body' in content,
            '<html' in content,
            len(content) > 2048  # Minimum content length
        ])

    async def _perform_cleanup(self, page):
        """Proper resource cleanup"""
        try:
            # Close current page if exists
            if page and not page.is_closed():
                await page.close()

            # Reset context to clear cookies/cache
            if self.context:
                await self.context.close()
                self.context = None

        except Exception as e:
            logging.warning(f"Cleanup error: {str(e)}")

    async def _close_page(self, page):
        """Safe page closure"""
        try:
            if page and not page.is_closed():
                await page.close()
        except Exception as e:
            logging.debug(f"Page closure warning: {str(e)}")

    async def close(self):
        """Full resource cleanup"""
        await self.etl.close()
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logging.warning(f"Shutdown error: {str(e)}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None

    async def crawl_website(self, base_url: str) -> list:
        """Crawl a domain and store product URLs with their domain names"""
        visited = set()
        to_visit = [base_url]
        product_urls = []

        # Initialize ETL system
        await self.etl.initialize()

        while to_visit:
            current_url = to_visit.pop(0)

            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                # Fetch page content
                html = await self.fetch_page(current_url)
            except Exception as e:
                logging.error(f"Failed to crawl {current_url}: {str(e)[:100]}")
                continue

            # Process page content
            soup = BeautifulSoup(html, 'html.parser')
            new_links = self._extract_links(soup, base_url, visited)

            # Analyze and store product URLs
            for link in new_links:
                if self.is_product_url(link):
                    # Extract domain name from the product URL
                    parsed_url = urlparse(link)
                    domain_name = parsed_url.netloc  # e.g., "www.flipkart.com"

                    # Store in database
                    await self.etl.pipeline(link, domain_name)
                    product_urls.append(link)

            # Add new links to crawling queue
            to_visit.extend(new_links)

        return product_urls

    def _extract_links(self, soup: BeautifulSoup, base_url: str, visited: set) -> list:
        """Extract and validate links from page content"""
        new_links = []
        for link in soup.find_all('a', href=True):
            try:
                full_url = urljoin(base_url, link['href'])
                full_url, _ = urldefrag(full_url)
                if (full_url.startswith(base_url) and
                        full_url not in visited and
                        not any(x in full_url for x in ["/help/", "/contact/"])):
                    new_links.append(full_url)
            except Exception as e:
                logging.warning(f"Link processing error: {str(e)[:50]}")
        return new_links

    def is_product_url(self, url: str) -> bool:
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
            r"/store/", r"/shop/", r"/list/", r"/filter"
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

    async def crawl_websites(self, domains: list) -> list:
        """Crawl multiple domains with staggered execution"""
        results = []
        tasks = []

        for idx, domain in enumerate(domains):
            tasks.append(
                self._crawl_domain_with_retry(
                    domain=domain,
                    delay=idx * 3
                )
            )

        domain_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in domain_results:
            if isinstance(result, Exception):
                logging.error(f"Domain failed: {str(result)[:100]}")
            elif result:
                results.extend(result)

        return results

    async def _crawl_domain_with_retry(self, domain: str, delay: int):
        """Domain crawling with retry logic"""
        await asyncio.sleep(delay)
        for attempt in range(3):
            try:
                logging.info(f"Starting {domain} (attempt {attempt + 1})")
                return await self.crawl_website(domain)
            except Exception as e:
                logging.warning(f"Domain failure ({domain}): {str(e)[:50]}")
                await self._safe_close()
                await asyncio.sleep(2 ** attempt)
        return []

    async def _safe_close(self):
        """Safely close browser resources"""
        try:
            if hasattr(self, 'context') and self.context:
                await self.context.close()
                self.context = None
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logging.warning(f"Cleanup error: {str(e)}")
        finally:
            self._initialization_attempted = False
            logging.info("Browser resources released")
