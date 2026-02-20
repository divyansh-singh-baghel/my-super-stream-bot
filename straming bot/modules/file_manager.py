import os
import secrets
import time
import asyncio
import logging
import shutil
from typing import Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self):
        # Memory map: token -> {path, user_id, timestamp, mime_type}
        self.videos: Dict[str, dict] = {}
        # User Concurrency map: user_id -> boolean (True if processing)
        self.user_locks: Dict[int, bool] = {}

    def generate_token(self) -> str:
        """Generate a random URL-safe token."""
        return secrets.token_urlsafe(16)

    def is_user_locked(self, user_id: int) -> bool:
        """Check if user is currently processing a video."""
        return self.user_locks.get(user_id, False)

    def lock_user(self, user_id: int):
        self.user_locks[user_id] = True

    def unlock_user(self, user_id: int):
        if user_id in self.user_locks:
            del self.user_locks[user_id]

    def add_video(self, user_id: int, file_path: str, mime_type: str = "video/mp4") -> str:
        """Register a video and return access token."""
        token = self.generate_token()
        self.videos[token] = {
            "path": file_path,
            "user_id": user_id,
            "created_at": time.time(),
            "mime": mime_type
        }
        return token

    def get_video_path(self, token: str) -> Optional[str]:
        data = self.videos.get(token)
        if not data:
            return None
        return data["path"]
    
    def get_video_mime(self, token: str) -> str:
        data = self.videos.get(token)
        return data.get("mime", "video/mp4") if data else "video/mp4"

    async def cleanup_loop(self):
        """Background task to delete expired files."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            now = time.time()
            expired_tokens = []

            # Identify expired
            for token, data in self.videos.items():
                if now - data["created_at"] > Config.EXPIRY_SECONDS:
                    expired_tokens.append(token)

            # Delete
            for token in expired_tokens:
                data = self.videos.pop(token)
                file_path = data["path"]
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"♻️ Cleaned up expired video: {file_path}")
                    except Exception as e:
                        logger.error(f"❌ Error deleting file {file_path}: {e}")

    def purge_all(self):
        """Cleanup on shutdown/restart."""
        logger.info("🧹 Purging all storage...")
        if os.path.exists(Config.STORAGE_DIR):
            shutil.rmtree(Config.STORAGE_DIR)
            os.makedirs(Config.STORAGE_DIR)

# Global Instance
file_manager = FileManager()
