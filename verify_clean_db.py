#!/usr/bin/env python3
"""
Verify database is clean and schema is properly applied
"""
import psycopg2
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

def check_database():
    """Check if database is clean and ready"""
    print("🔍 Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check key tables
    tables_to_check = [
        ('games', 'SELECT COUNT(*) FROM games'),
        ('video_demonstrations', 'SELECT COUNT(*) FROM video_demonstrations'),
        ('learning_sessions', 'SELECT COUNT(*) FROM learning_sessions'),
        ('video_frames', 'SELECT COUNT(*) FROM video_frames'),
        ('game_knowledge', 'SELECT COUNT(*) FROM game_knowledge'),
    ]
    
    print("\n📊 Database Status:")
    print("-" * 50)
    
    all_clean = True
    for table_name, query in tables_to_check:
        try:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            status = "✅ CLEAN" if count == 0 else f"⚠️  {count} rows"
            print(f"{table_name:25} {status}")
            if count > 0:
                all_clean = False
        except Exception as e:
            print(f"{table_name:25} ❌ ERROR: {e}")
            all_clean = False
    
    print("-" * 50)
    
    if all_clean:
        print("\n✅ Database is clean and ready for fresh start!")
    else:
        print("\n⚠️  Database has existing data")
    
    cursor.close()
    conn.close()
    
    return all_clean

if __name__ == "__main__":
    check_database()
