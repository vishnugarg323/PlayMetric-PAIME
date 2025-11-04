"""
Database connection and utilities for PlayMetric services
"""

import os
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis

# Database configuration
DB_USER = os.getenv("DB_USER", "playmetric")
DB_PASSWORD = os.getenv("DB_PASSWORD", "playmetric123")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "playmetric")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Connection strings
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ASYNCPG_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy setup
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Redis connection pool
redis_pool: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection pool"""
    global redis_pool
    redis_pool = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        max_connections=50
    )
    return redis_pool


async def close_redis():
    """Close Redis connection pool"""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


def get_redis() -> redis.Redis:
    """Get Redis connection"""
    if not redis_pool:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_pool


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_asyncpg_pool() -> asyncpg.Pool:
    """Create asyncpg connection pool for raw SQL queries"""
    return await asyncpg.create_pool(
        ASYNCPG_URL,
        min_size=10,
        max_size=50,
        command_timeout=60
    )


class DatabaseManager:
    """Central database manager for all services"""
    
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
