# etl.py
import logging
import asyncio
from typing import Optional
from src.product_urls_table import ProductURLsManagementSystem

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class ETL:
    def __init__(self, table_name: str = "product_urls"):
        """
        Initialize ETL system with database connection
        Args:
            table_name: Name of the table to store URLs
        """
        self.table_name = table_name
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.url_manager: Optional[ProductURLsManagementSystem] = None

    async def initialize(self):
        """Async initialization for database connection"""
        self.url_manager = ProductURLsManagementSystem(self.table_name)
        logging.info("ETL system initialized with database connection")

    async def pipeline(self, url: str, domain_name: str):
        """
        Store URL with retry logic and error handling
        Args:
            url: Product URL to store
        """
        if not self.url_manager:
            await self.initialize()

        for attempt in range(self.max_retries):
            try:
                self.url_manager.insert_one(url, domain_name)
                logging.info(f"Stored URL: {url}")
                return
            except Exception as e:
                logging.warning(
                    f"Storage failed (attempt {attempt + 1}/{self.max_retries}): {url} - {str(e)[:100]}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay ** (attempt + 1))
                else:
                    logging.error(f"Permanent storage failure: {url}")
                    # Add to dead-letter queue or error handling here
                    raise

    async def close(self):
        """Clean up resources"""
        if self.url_manager and self.url_manager.db_connection:
            self.url_manager.db_connection.conn.disconnect()
            logging.info("Database connection closed")