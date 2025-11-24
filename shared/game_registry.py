"""
Game Registry - Links APKs, Knowledge Bases, and AI Configuration

This module manages the relationship between:
1. Uploaded APKs (package names)
2. Learned knowledge bases (from videos)
3. AI playing configuration
4. Device settings
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GameRegistry:
    """Centralized registry for game metadata and AI configuration"""
    
    def __init__(self, registry_path: str = "/data/game_registry.json"):
        self.registry_path = Path(registry_path)
        self.games: Dict[str, Dict[str, Any]] = {}
        self.load()
    
    def load(self):
        """Load registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self.games = json.load(f)
                logger.info(f"📚 Loaded {len(self.games)} games from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.games = {}
        else:
            self.games = {}
            self.save()
    
    def save(self):
        """Save registry to disk"""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, 'w') as f:
                json.dump(self.games, f, indent=2)
            logger.info(f"💾 Saved registry with {len(self.games)} games")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_game(
        self,
        game_id: str,
        display_name: str,
        apk_path: Optional[str] = None,
        package_name: Optional[str] = None,
        knowledge_base_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new game or update existing
        
        Args:
            game_id: Unique identifier (e.g., "subway_surfers")
            display_name: Human-readable name (e.g., "Subway Surfers")
            apk_path: Path to APK file
            package_name: Android package name (e.g., "com.kiloo.subwaysurf")
            knowledge_base_path: Path to learned knowledge JSON
            metadata: Additional metadata (version, difficulty, etc.)
        """
        if game_id not in self.games:
            self.games[game_id] = {
                "game_id": game_id,
                "display_name": display_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "apk": {
                    "path": None,
                    "package_name": None,
                    "version": None,
                    "uploaded_at": None
                },
                "knowledge": {
                    "base_path": None,
                    "learned_from_video": None,
                    "last_updated": None,
                    "scenes_count": 0,
                    "buttons_count": 0,
                    "strategies_count": 0
                },
                "ai_config": {
                    "use_gemini": True,
                    "cycle_delay": 2.0,
                    "max_cycles": None,
                    "decision_confidence_threshold": 0.6
                },
                "device": {
                    "preferred_ip": None,
                    "screen_width": None,
                    "screen_height": None
                },
                "status": "registered",  # registered, apk_installed, knowledge_ready, playing
                "metadata": metadata or {}
            }
            logger.info(f"🎮 Registered new game: {display_name} ({game_id})")
        
        # Update fields
        game = self.games[game_id]
        game["updated_at"] = datetime.now().isoformat()
        
        if apk_path:
            game["apk"]["path"] = apk_path
            game["apk"]["uploaded_at"] = datetime.now().isoformat()
            if game["status"] == "registered":
                game["status"] = "apk_uploaded"
        
        if package_name:
            game["apk"]["package_name"] = package_name
        
        if knowledge_base_path:
            game["knowledge"]["base_path"] = knowledge_base_path
            game["knowledge"]["last_updated"] = datetime.now().isoformat()
            if game["status"] == "apk_uploaded":
                game["status"] = "knowledge_ready"
        
        if metadata:
            game["metadata"].update(metadata)
        
        self.save()
        return game
    
    def link_video_learning(
        self,
        game_id: str,
        video_path: str,
        knowledge_base_path: str,
        stats: Optional[Dict[str, int]] = None
    ):
        """Link video learning results to a game"""
        if game_id not in self.games:
            raise ValueError(f"Game {game_id} not registered. Register it first.")
        
        game = self.games[game_id]
        game["knowledge"]["base_path"] = knowledge_base_path
        game["knowledge"]["learned_from_video"] = video_path
        game["knowledge"]["last_updated"] = datetime.now().isoformat()
        
        if stats:
            game["knowledge"]["scenes_count"] = stats.get("scenes", 0)
            game["knowledge"]["buttons_count"] = stats.get("buttons", 0)
            game["knowledge"]["strategies_count"] = stats.get("strategies", 0)
        
        # Update status
        if game["apk"]["path"]:
            game["status"] = "ready_to_play"
        else:
            game["status"] = "knowledge_ready"
        
        game["updated_at"] = datetime.now().isoformat()
        self.save()
        
        logger.info(f"🧠 Linked knowledge base to {game['display_name']}")
    
    def link_apk(
        self,
        game_id: str,
        apk_path: str,
        package_name: str,
        version: Optional[str] = None
    ):
        """Link an installed APK to a game"""
        if game_id not in self.games:
            raise ValueError(f"Game {game_id} not registered. Register it first.")
        
        game = self.games[game_id]
        game["apk"]["path"] = apk_path
        game["apk"]["package_name"] = package_name
        game["apk"]["version"] = version
        game["apk"]["uploaded_at"] = datetime.now().isoformat()
        
        # Update status
        if game["knowledge"]["base_path"]:
            game["status"] = "ready_to_play"
        else:
            game["status"] = "apk_installed"
        
        game["updated_at"] = datetime.now().isoformat()
        self.save()
        
        logger.info(f"📱 Linked APK to {game['display_name']}: {package_name}")
    
    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get game configuration by ID"""
        return self.games.get(game_id)
    
    def get_by_package_name(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Find game by Android package name"""
        for game in self.games.values():
            if game["apk"]["package_name"] == package_name:
                return game
        return None
    
    def list_games(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all games, optionally filtered by status"""
        games = list(self.games.values())
        if status:
            games = [g for g in games if g["status"] == status]
        return games
    
    def is_ready_to_play(self, game_id: str) -> bool:
        """Check if game has both APK and knowledge base"""
        game = self.get_game(game_id)
        if not game:
            return False
        
        has_apk = game["apk"]["path"] is not None
        has_knowledge = game["knowledge"]["base_path"] is not None
        
        return has_apk and has_knowledge
    
    def get_knowledge_base_path(self, game_id: str) -> Optional[str]:
        """Get knowledge base path for a game"""
        game = self.get_game(game_id)
        return game["knowledge"]["base_path"] if game else None
    
    def get_package_name(self, game_id: str) -> Optional[str]:
        """Get Android package name for a game"""
        game = self.get_game(game_id)
        return game["apk"]["package_name"] if game else None
    
    def update_ai_config(self, game_id: str, config: Dict[str, Any]):
        """Update AI playing configuration"""
        if game_id not in self.games:
            raise ValueError(f"Game {game_id} not registered")
        
        self.games[game_id]["ai_config"].update(config)
        self.games[game_id]["updated_at"] = datetime.now().isoformat()
        self.save()
    
    def update_status(self, game_id: str, status: str):
        """Update game status"""
        if game_id not in self.games:
            raise ValueError(f"Game {game_id} not registered")
        
        valid_statuses = [
            "registered", "apk_uploaded", "apk_installed",
            "knowledge_ready", "ready_to_play", "playing", "paused"
        ]
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        
        self.games[game_id]["status"] = status
        self.games[game_id]["updated_at"] = datetime.now().isoformat()
        self.save()


# Singleton instance
_registry = None

def get_registry() -> GameRegistry:
    """Get global game registry instance"""
    global _registry
    if _registry is None:
        _registry = GameRegistry()
    return _registry
