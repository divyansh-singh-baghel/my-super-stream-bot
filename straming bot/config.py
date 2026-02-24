import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "12345")) # Apna API ID daalna
    API_HASH = os.getenv("API_HASH", "your_api_hash")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 
    
    PORT = int(os.getenv("PORT", 8080)) 
    HOST = "0.0.0.0"
    BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")
    STORAGE_DIR = "storage"
    
    # 👇 NAYA FEATURE: Smart Limits
    EXPIRY_SECONDS = 24 * 60 * 60  # 24 Hours ke baad link expire
    # 2 GB limit in bytes (2 * 1024 * 1024 * 1024)
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 2147483648)) 

if not os.path.exists(Config.STORAGE_DIR):
    os.makedirs(Config.STORAGE_DIR)
