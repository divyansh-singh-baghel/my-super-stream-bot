import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API (Get from my.telegram.org)
    API_ID = int(os.getenv("API_ID", "12345"))
    API_HASH = os.getenv("API_HASH", "your_api_hash")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

    # Web Server Config
    # Render provides PORT automatically
    PORT = int(os.getenv("PORT", 8080)) 
    HOST = "0.0.0.0"
    
    # Domain (Used for generating links)
    # On Render, this is: https://your-app-name.onrender.com
    BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")

    # Paths
    STORAGE_DIR = "storage"
    
    # Limits
    EXPIRY_SECONDS = 24 * 60 * 60  # 24 Hours
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_random_key")

# Ensure storage exists
if not os.path.exists(Config.STORAGE_DIR):
    os.makedirs(Config.STORAGE_DIR)