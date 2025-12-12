"""
Shared modules for PlayMetric services
"""

# For services that DON'T use SQLAlchemy (learning, ai-player):
# Use asyncpg_manager which has no sqlalchemy dependency
from .asyncpg_manager import DatabaseManager

__all__ = ["DatabaseManager"]

# For services that need SQLAlchemy (orchestrator, etc):
# Import directly: from shared.database import get_db_session, etc
