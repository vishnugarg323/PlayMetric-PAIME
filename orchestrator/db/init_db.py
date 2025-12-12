"""
Database initialization script - runs schema.sql on startup
Creates all tables, indexes, triggers, and functions if they don't exist
Safe to run multiple times (idempotent)
"""
import asyncio
import asyncpg
import os

async def init_database():
    """Initialize database from schema.sql file"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    print("🔧 Initializing database schema from schema.sql...")
    
    # Read the schema file from shared folder
    schema_path = '/app/shared/schema.sql'
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Schema file not found: {schema_path}")
        return
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Execute the entire schema
        await conn.execute(schema_sql)
        
        # Verify table count
        result = await conn.fetchrow("""
            SELECT COUNT(*) as table_count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        
        print(f"✅ Database initialized successfully! Total tables: {result['table_count']}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_database())
