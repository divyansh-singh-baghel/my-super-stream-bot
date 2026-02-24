import os
import secrets
import time
import asyncio
import logging
import shutil
from typing import Dict, Set, Optional
from config import Config

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self):
        # Video tracking
        self.videos: Dict[str, dict] = {}
        self.user_locks: Dict[int, bool] = {}
        
        # 👑 BOSS MODE FEATURES
        self.banned_users: Set[int] = set()
        self.user_stats: Dict[int, int] = {}  # Spammers ko track karne ke liye
        
        # 👇 NAYA FEATURE: Channel Posts ki qualities yaad rakhne ke liye
        self.post_mappings: Dict[str, dict] = {} 
        
        # Dynamic Settings
        self.settings = {
            "expiry": Config.EXPIRY_SECONDS,
            "maintenance": False
        }

    def generate_token(self) -> str:
        return secrets.token_urlsafe(16)

    # --- Multi-Quality Channel Link Mapping (Hacker Backend) ---
    
    def save_post_mapping(self, mapping_data: dict) -> str:
        """Channel post ke links ko ek chote code (post_id) se map karta hai."""
        post_id = secrets.token_hex(4) # Ek unique short code banayega
        self.post_mappings[post_id] = mapping_data
        return post_id

    def get_post_mapping(self, post_id: str) -> dict:
        """User jab DM me aayega toh ye function usko sahi link dega."""
        return self.post_mappings.get(post_id, {})

    # --- User Control & Anti-Spam ---
    
    def is_banned(self, user_id: int) -> bool:
        return user_id in self.banned_users

    def ban_user(self, user_id: int):
        self.banned_users.add(user_id)

    def unban_user(self, user_id: int):
        self.banned_users.discard(user_id)

    def track_user_activity(self, user_id: int):
        """User ka score badhata hai taaki spammer pakda ja sake."""
        self.user_stats[user_id] = self.user_stats.get(user_id, 0) + 1

    def get_top_users(self) -> str:
        """Top 5 users ki list return karega /stats ke liye."""
        if not self.user_stats:
            return "No active users yet."
        sorted_users = sorted(self.user_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        text = ""
        for uid, count in sorted_users:
            text += f"👤 `{uid}` : {count} videos\n"
        return text

    # --- Concurrency ---

    def is_user_locked(self, user_id: int) -> bool:
        return self.user_locks.get(user_id, False)

    def lock_user(self, user_id: int):
        self.user_locks[user_id] = True

    def unlock_user(self, user_id: int):
        if user_id in self.user_locks:
            del self.user_locks[user_id]

    # --- Video Management ---

    def add_video(self, user_id: int, file_path: str, mime_type: str = "video/mp4") -> str:
        token = self.generate_token()
        self.videos[token] = {
            "path": file_path,
            "user_id": user_id,
            "created_at": time.time(),
            "mime": mime_type
        }
        self.track_user_activity(user_id)
        return token

    def get_video_path(self, token: str) -> Optional[str]:
        data = self.videos.get(token)
        return data["path"] if data else None

    def delete_video(self, token: str) -> bool:
        data = self.videos.pop(token, None)
        if data and os.path.exists(data["path"]):
            try:
                os.remove(data["path"])
                return True
            except Exception:
                pass
        return False

    async def cleanup_loop(self):
        """Dynamic expiry time ke hisaab se videos delete karega."""
        while True:
            await asyncio.sleep(60)
            now = time.time()
            expired_tokens = []
            
            current_expiry = self.settings["expiry"]

            for token, data in list(self.videos.items()):
                if now - data["created_at"] > current_expiry:
                    expired_tokens.append(token)

            for token in expired_tokens:
                self.delete_video(token)
                logger.info(f"♻️ Cleaned up expired video token: {token}")

    def purge_all(self):
        logger.info("🧹 Purging all storage...")
        if os.path.exists(Config.STORAGE_DIR):
            shutil.rmtree(Config.STORAGE_DIR)
            os.makedirs(Config.STORAGE_DIR)

# Global Instance
file_manager = FileManager()
