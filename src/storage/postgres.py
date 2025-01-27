from asyncpg import create_pool  # Add this import


class AsyncPostgres:
    def __init__(self):
        self.pool = None  # Connection pool

    async def connect(self, config):
        """Initialize connection pool"""
        self.pool = await create_pool(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            database=config['database'],
            min_size=1,
            max_size=100
        )

    async def bulk_insert_urls(self, batch):
        """Use connection pool for batch inserts"""
        async with self.pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO product_urls (url, domain) VALUES ($1, $2)",
                batch
            )

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()