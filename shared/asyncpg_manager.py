"""
Simple asyncpg-only database manager (no SQLAlchemy dependency)
For learning and ai-player services
"""

import os
from typing import Optional
import asyncpg
import redis.asyncio as redis

# Database configuration
# Support Railway DATABASE_URL or individual components
RAILWAY_DATABASE_URL = os.getenv("DATABASE_URL")  # Railway provides this

if RAILWAY_DATABASE_URL:
    ASYNCPG_URL = RAILWAY_DATABASE_URL
else:
    # Use individual components for local docker-compose
    DB_USER = os.getenv("DB_USER", "playmetric")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "playmetric123")
    DB_HOST = os.getenv("DB_HOST", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "playmetric")
    ASYNCPG_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Global connection pool
_asyncpg_pool: Optional[asyncpg.Pool] = None
_redis_client: Optional[redis.Redis] = None


async def get_asyncpg_pool() -> asyncpg.Pool:
    """Get or create asyncpg connection pool"""
    global _asyncpg_pool
    if not _asyncpg_pool:
        _asyncpg_pool = await asyncpg.create_pool(
            ASYNCPG_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _asyncpg_pool


async def init_redis() -> redis.Redis:
    """Initialize Redis connection"""
    global _redis_client
    if not _redis_client:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
    return _redis_client


async def get_redis() -> redis.Redis:
    """Get Redis client (initialize if needed)"""
    if not _redis_client:
        return await init_redis()
    return _redis_client


async def close_redis():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class DatabaseManager:
    """Central database manager using asyncpg only (no SQLAlchemy)"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize all database connections"""
        self.pool = await get_asyncpg_pool()
        self.redis = await init_redis()
    
    async def disconnect(self):
        """Close all database connections"""
        if self.pool:
            await self.pool.close()
        if self.redis:
            await close_redis()
    
    async def execute(self, query: str, *args):
        """Execute a query and return results"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def execute_one(self, query: str, *args):
        """Execute a query and return first result"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def execute_write(self, query: str, *args):
        """Execute an insert/update/delete query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def execute_read(self, query: str, *args):
        """Execute a read query and return all results (alias for execute)"""
        return await self.execute(query, *args)
    
    async def execute_many(self, query: str, *args):
        """Execute a query and return multiple results (alias for execute)"""
        return await self.execute(query, *args)
    
    async def cache_get(self, key: str) -> Optional[str]:
        """Get value from Redis cache"""
        return await self.redis.get(key)
    
    async def cache_set(self, key: str, value: str, expiry: int = 3600):
        """Set value in Redis cache with expiry in seconds"""
        await self.redis.set(key, value, ex=expiry)
    
    async def cache_delete(self, key: str):
        """Delete key from Redis cache"""
        await self.redis.delete(key)
    
    async def cache_exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        return await self.redis.exists(key) > 0


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get or create database manager instance"""
    global db_manager
    if not db_manager:
        db_manager = DatabaseManager()
        await db_manager.connect()
    return db_manager


async def close_db_manager():
    """Close database manager"""
    global db_manager
    if db_manager:
        await db_manager.disconnect()
        db_manager = None
