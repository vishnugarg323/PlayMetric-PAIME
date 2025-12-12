#!/usr/bin/env python3
"""
Drop all tables and recreate from schema.sql
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'turntable.proxy.rlwy.net'),
    'port': int(os.getenv('DB_PORT', 16049)),
    'user': os.getenv('DB_USER', 'railway'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'railway')
}

def recreate_database():
    """Drop all tables and recreate from schema.sql"""
    DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    print("Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("🗑️  Dropping all tables...")
    try:
        # Drop all tables in cascade to handle foreign keys
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        print("✅ All tables dropped")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        raise
    
    print("\n📖 Reading schema.sql...")
    with open("shared/schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    print("🏗️  Creating tables from schema...")
    try:
        cursor.execute(schema_sql)
        print("✅ Schema applied successfully!")
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    recreate_database()
