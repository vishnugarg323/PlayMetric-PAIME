import asyncpg
import aioredis
from typing import Optional
import os

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Initialize database connections"""
        # PostgreSQL connection
        self.pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL", "postgresql://paime:paime123@db:5432/paime"),
            min_size=10,
            max_size=20
        )
        
        # Redis connection
        self.redis = await aioredis.create_redis_pool(
            os.getenv("REDIS_URL", "redis://redis:6379")
        )
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
    
    async def execute(self, query: str, *args):
        """Execute a query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

# Global database instance
db = Database()