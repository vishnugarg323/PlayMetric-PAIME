"""
Quick database clear script - run inside Docker container
"""
import asyncio
import os
import sys
sys.path.insert(0, '/app/shared')

from database import DatabaseManager

async def clear_all():
    db = DatabaseManager()
    await db.connect()
    
    try:
        print("🧹 Clearing database tables...")
        
        # Delete in correct order (only tables that exist)
        tables = [
            "video_analysis_frames",
            "video_demonstrations", 
            "ai_actions",
            "session_metrics",
            "sessions",
            "game_versions",
            "games"
        ]
        
        for table in tables:
            try:
                result = await db.pool.execute(f"DELETE FROM {table} CASCADE")
                print(f"✓ {table}: {result}")
            except Exception as e:
                print(f"⚠️  {table}: {str(e)[:50]}")
        
        # Reset sequences
        print("\n🔄 Resetting sequences...")
        sequences = [
            "games_id_seq",
            "game_versions_id_seq",
            "sessions_id_seq",
            "video_demonstrations_id_seq"
        ]
        
        for seq in sequences:
            try:
                await db.pool.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                print(f"✓ {seq}")
            except:
                pass
        
        print("\n✅ Database cleared!")
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(clear_all())
