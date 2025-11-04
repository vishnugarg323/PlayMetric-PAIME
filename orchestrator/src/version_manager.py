"""
APK Upload and Version Management System
Handles APK upload, parsing, storage, and version tracking
"""

import os
import hashlib
import shutil
from typing import Dict, Optional
from datetime import datetime
import subprocess
import json
import logging
import sys

sys.path.append('/app/shared')
from database import DatabaseManager

logger = logging.getLogger(__name__)


class APKParser:
    """Parse APK file and extract metadata"""
    
    @staticmethod
    def get_apk_info(apk_path: str) -> Dict:
        """Extract APK information using aapt"""
        try:
            # Run aapt dump badging
            result = subprocess.run(
                ['aapt', 'dump', 'badging', apk_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"aapt failed: {result.stderr}")
            
            output = result.stdout
            info = {}
            
            # Parse package name
            for line in output.split('\n'):
                if line.startswith('package:'):
                    parts = line.split()
                    for part in parts:
                        if part.startswith('name='):
                            info['package_name'] = part.split('=')[1].strip("'\"")
                        elif part.startswith('versionCode='):
                            info['version_code'] = int(part.split('=')[1].strip("'\""))
                        elif part.startswith('versionName='):
                            info['version_name'] = part.split('=')[1].strip("'\"")
                
                # Parse SDK versions
                if line.startswith('sdkVersion:'):
                    info['min_sdk'] = int(line.split(':')[1].strip().strip("'\""))
                elif line.startswith('targetSdkVersion:'):
                    info['target_sdk'] = int(line.split(':')[1].strip().strip("'\""))
            
            return info
            
        except subprocess.TimeoutExpired:
            raise Exception("APK parsing timed out")
        except Exception as e:
            logger.error(f"Error parsing APK: {e}")
            raise


class APKManager:
    """Manages APK file storage and versioning"""
    
    def __init__(self, storage_path: str = "/apks"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def calculate_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)
    
    def store_apk(self, source_path: str, game_id: str, version_name: str) -> str:
        """Store APK file with organized structure"""
        # Create game-specific directory
        game_dir = os.path.join(self.storage_path, game_id)
        os.makedirs(game_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{version_name.replace('.', '_')}.apk"
        dest_path = os.path.join(game_dir, filename)
        
        # Copy file
        shutil.copy2(source_path, dest_path)
        
        logger.info(f"APK stored: {dest_path}")
        return dest_path


class VersionComparisonService:
    """Compares two game versions for changes"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def compare_versions(self, version1_id: str, version2_id: str) -> Dict:
        """Generate comprehensive version comparison"""
        # Get version details
        v1 = await self.db.execute_one(
            "SELECT * FROM game_versions WHERE id = $1", version1_id
        )
        v2 = await self.db.execute_one(
            "SELECT * FROM game_versions WHERE id = $2", version2_id
        )
        
        if not v1 or not v2:
            raise ValueError("Version not found")
        
        # Get bug statistics for each version
        v1_bugs = await self.db.execute(
            """SELECT severity, COUNT(*) as count
               FROM bugs
               WHERE version_id = $1
               GROUP BY severity""",
            version1_id
        )
        
        v2_bugs = await self.db.execute(
            """SELECT severity, COUNT(*) as count
               FROM bugs
               WHERE version_id = $1
               GROUP BY severity""",
            version2_id
        )
        
        # Get crash statistics
        v1_crash_rate = await self.db.execute_one(
            """SELECT 
                   COUNT(DISTINCT CASE WHEN b.type = 'crash' THEN b.id END)::float / 
                   NULLIF(COUNT(DISTINCT s.id), 0) as crash_rate
               FROM sessions s
               LEFT JOIN bugs b ON b.session_id = s.id
               WHERE s.version_id = $1""",
            version1_id
        )
        
        v2_crash_rate = await self.db.execute_one(
            """SELECT 
                   COUNT(DISTINCT CASE WHEN b.type = 'crash' THEN b.id END)::float / 
                   NULLIF(COUNT(DISTINCT s.id), 0) as crash_rate
               FROM sessions s
               LEFT JOIN bugs b ON b.session_id = s.id
               WHERE s.version_id = $1""",
            version2_id
        )
        
        # Get regression bugs (bugs in v2 not in v1)
        regressions = await self.db.execute(
            """SELECT b2.*
               FROM bugs b2
               WHERE b2.version_id = $2
               AND NOT EXISTS (
                   SELECT 1 FROM bugs b1
                   WHERE b1.version_id = $1
                   AND b1.type = b2.type
                   AND b1.title = b2.title
               )""",
            version1_id, version2_id
        )
        
        # Get fixed bugs (bugs in v1 not in v2)
        fixed_bugs = await self.db.execute(
            """SELECT b1.*
               FROM bugs b1
               WHERE b1.version_id = $1
               AND NOT EXISTS (
                   SELECT 1 FROM bugs b2
                   WHERE b2.version_id = $2
                   AND b2.type = b1.type
                   AND b2.title = b1.title
               )""",
            version1_id, version2_id
        )
        
        # Calculate metrics delta
        comparison = {
            "version1": {
                "id": version1_id,
                "version_name": v1['version_name'],
                "version_code": v1['version_code'],
                "bugs": {row['severity']: row['count'] for row in v1_bugs},
                "crash_rate": v1_crash_rate['crash_rate'] if v1_crash_rate else 0
            },
            "version2": {
                "id": version2_id,
                "version_name": v2['version_name'],
                "version_code": v2['version_code'],
                "bugs": {row['severity']: row['count'] for row in v2_bugs},
                "crash_rate": v2_crash_rate['crash_rate'] if v2_crash_rate else 0
            },
            "regressions": len(regressions),
            "fixed_bugs": len(fixed_bugs),
            "crash_rate_delta": (v2_crash_rate['crash_rate'] if v2_crash_rate else 0) - 
                               (v1_crash_rate['crash_rate'] if v1_crash_rate else 0),
            "regression_details": regressions,
            "fixed_bug_details": fixed_bugs
        }
        
        # Store comparison in database
        await self.db.execute_write(
            """INSERT INTO version_comparisons 
               (version1_id, version2_id, comparison_data, created_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (version1_id, version2_id) 
               DO UPDATE SET comparison_data = $3, created_at = NOW()""",
            version1_id, version2_id, comparison
        )
        
        return comparison


class VersionTracker:
    """Track and manage game versions"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.apk_manager = APKManager()
        self.comparison_service = VersionComparisonService(db)
    
    async def upload_version(
        self,
        game_id: str,
        apk_file_path: str,
        uploaded_by: Optional[str] = None
    ) -> Dict:
        """Upload and register new game version"""
        try:
            # Parse APK
            logger.info(f"Parsing APK: {apk_file_path}")
            apk_info = APKParser.get_apk_info(apk_file_path)
            
            # Calculate hash and size
            apk_hash = self.apk_manager.calculate_hash(apk_file_path)
            apk_size = self.apk_manager.get_file_size(apk_file_path)
            
            # Check if version already exists
            existing = await self.db.execute_one(
                """SELECT id FROM game_versions 
                   WHERE game_id = $1 AND apk_hash = $2""",
                game_id, apk_hash
            )
            
            if existing:
                raise Exception(f"Version already exists with ID: {existing['id']}")
            
            # Store APK file
            stored_path = self.apk_manager.store_apk(
                apk_file_path,
                game_id,
                apk_info['version_name']
            )
            
            # Insert version record
            import json
            version_id = await self.db.execute_one(
                """INSERT INTO game_versions 
                   (game_id, version_name, version_code, apk_path, apk_size_bytes, 
                    apk_hash, min_sdk_version, target_sdk_version, uploaded_by, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                   RETURNING id""",
                game_id,
                apk_info['version_name'],
                apk_info['version_code'],
                stored_path,
                apk_size,
                apk_hash,
                apk_info.get('min_sdk'),
                apk_info.get('target_sdk'),
                uploaded_by,
                json.dumps(apk_info)  # Convert dict to JSON string
            )
            
            logger.info(f"Version {apk_info['version_name']} registered: {version_id['id']}")
            
            return {
                "version_id": version_id['id'],
                "version_name": apk_info['version_name'],
                "version_code": apk_info['version_code'],
                "apk_hash": apk_hash,
                "apk_size": apk_size,
                "stored_path": stored_path
            }
            
        except Exception as e:
            logger.error(f"Error uploading version: {e}", exc_info=True)
            raise
    
    async def get_version_history(self, game_id: str) -> list:
        """Get version history for a game"""
        versions = await self.db.execute(
            """SELECT v.*,
                   COUNT(DISTINCT s.id) as session_count,
                   COUNT(DISTINCT b.id) as bug_count
               FROM game_versions v
               LEFT JOIN sessions s ON s.version_id = v.id
               LEFT JOIN bugs b ON b.version_id = v.id
               WHERE v.game_id = $1
               GROUP BY v.id
               ORDER BY v.version_code DESC""",
            game_id
        )
        return versions
    
    async def compare_versions(self, version1_id: str, version2_id: str) -> Dict:
        """Compare two versions"""
        return await self.comparison_service.compare_versions(version1_id, version2_id)
    
    async def detect_regressions(self, new_version_id: str) -> list:
        """Detect regressions in new version compared to previous"""
        # Get previous version
        version = await self.db.execute_one(
            "SELECT * FROM game_versions WHERE id = $1", new_version_id
        )
        
        if not version:
            return []
        
        # Find previous version
        prev_version = await self.db.execute_one(
            """SELECT * FROM game_versions 
               WHERE game_id = $1 AND version_code < $2
               ORDER BY version_code DESC LIMIT 1""",
            version['game_id'], version['version_code']
        )
        
        if not prev_version:
            return []
        
        # Compare versions
        comparison = await self.compare_versions(prev_version['id'], new_version_id)
        
        return comparison.get('regression_details', [])
