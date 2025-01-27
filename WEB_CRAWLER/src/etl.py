# etl.py
import logging
import os
from typing import Optional

from src.product_urls_table import ProductURLsManagementSystem

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class ETL:
    def __init__(self, db, table_name: str = "product_urls"):
        """
        Initialize ETL system with database connection
        Args:
            table_name: Name of the table to store URLs
        """
        self.table_name = table_name
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.url_manager: Optional[ProductURLsManagementSystem] = None
        self.db = db
        self.db_config = {
            'user': os.getenv("DATABASE_USER", "admin"),  # Add defaults
            'password': os.getenv("DATABASE_PASSWORD", "admin"),
            'host': os.getenv("DATABASE_HOST", "postgres"),  # Match Docker service name
            'port': os.getenv("DATABASE_PORT", "5432"),
            'database': os.getenv("DATABASE_NAME", "postgres")
        }

    async def initialize(self):
        """Initialize ETL with async table creation"""
        self.url_manager = ProductURLsManagementSystem(self.table_name, self.db)
        await self.url_manager.db_connection.connect(self.db_config)  # Connect async
        await self.url_manager.create_table()  # Explicit table creation
        logging.info("ETL system initialized")
