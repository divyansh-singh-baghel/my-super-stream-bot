import asyncio
import logging
import sys
from pyrogram import Client, idle
from config import Config
from modules.file_manager import file_manager
from modules.stream_server import start_web_server

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def main():
    # Client Setup
    app = Client(
        "TelegramStreamBot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="modules"),
        in_memory=True
    )
    
    # 1. Start Web Server
    server_task = asyncio.create_task(start_web_server())
    
    # 2. Start File Manager Cleanup Loop (Auto-Cleanup)
    cleanup_task = asyncio.create_task(file_manager.cleanup_loop())

    # 3. Start Telegram Bot
    try:
        await app.start()
        logger.info("🤖 Bot Started!")
        logger.info(f"Admin ID: {Config.ADMIN_ID}") 

        # Keep the bot running
        await idle()
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}")
    finally:
        # Graceful Shutdown
        logger.info("🛑 Stopping Bot...")
        await app.stop()
        server_task.cancel()
        cleanup_task.cancel()
        file_manager.purge_all()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
