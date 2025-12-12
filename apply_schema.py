#!/usr/bin/env python3
"""
Apply schema.sql to Railway PostgreSQL database
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

def apply_schema():
    """Apply the schema.sql file to the database"""
    DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    print("Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("Reading schema.sql...")
    with open("shared/schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    print("Applying schema...")
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
    apply_schema()
