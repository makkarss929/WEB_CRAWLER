import logging

from src.storage.postgres import AsyncPostgres


class ProductURLsManagementSystem:
    def __init__(self, table_name, db_connection=None, schema_name="public"):
        self.schema_name = schema_name
        self.table_name = table_name
        self.db_connection = db_connection or AsyncPostgres()

    async def create_table(self):
        """Create table using asyncpg connection pool"""
        async with self.db_connection.pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema_name}.{self.table_name} (
                    id BIGSERIAL PRIMARY KEY,
                    url TEXT UNIQUE,
                    domain TEXT
                );
            """)
            logging.info(f"Table {self.schema_name}.{self.table_name} created")
