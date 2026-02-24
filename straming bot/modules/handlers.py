import os
import time
import uuid
import logging
import aiohttp
import mimetypes
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from config import Config
from modules.file_manager import file_manager

logger = logging.getLogger(__name__)

# --- Utilities ---

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "
    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time

def format_bytes(size: float) -> str:
    """Converts bytes to a readable format (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

async def progress_bar(current, total, status_msg, start_time):
    """Updates the progress message during download."""
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        
        # Time remaining (ETA)
        time_to_completion = round((total - current) / speed) if speed > 0 else 0
        estimated_time = get_readable_time(time_to_completion)

        try:
            await status_msg.edit_text(
                f"📥 **Downloading...**\n"
                f"📊 Progress: {percentage:.2f}%\n"
                f"🚀 Speed: {format_bytes(speed)}/s\n"
                f"⏳ ETA: {estimated_time}"
            )
        except Exception:
            pass

def get_safe_base_url() -> str:
    """Ensures the BASE_URL has https:// and no trailing slash."""
    url = Config.BASE_URL.rstrip('/')
    if not url.startswith("http"):
        url = "https://" + url
    return url

# --- Handlers ---

@Client.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    # 👇 NAYA FEATURE: Deep Link Checker
    if len(message.command) > 1 and message.command[1].startswith("watch_"):
        post_id = message.command[1].replace("watch_", "")
        mapping = file_manager.get_post_mapping(post_id)
        
        if not mapping:
            return await message.reply_text("❌ This link has expired or is invalid.")
            
        # User ko wahi qualities dikhana jo post mein thi
        buttons = []
        for quality_name, msg_id in mapping.items():
            # Yahan callback data ban raha hai jo hum next step mein process karenge
            buttons.append([InlineKeyboardButton(quality_name, callback_data=f"fetch_{msg_id}")])
            
        await message.reply_text(
            "🎬 **Video Found!**\n\nPlease select your preferred quality to start streaming:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # Normal Start Message
        await message.reply_text(
            "👋 **Hello! I am a Video Streaming Bot.**\n\n"
            "📤 **Send me a video file** or a **direct download link**.\n"
            "🔗 I will generate a temporary public streaming link for you.\n\n"
            "⚠️ _Links expire based on Admin settings._"
        )

@Client.on_message(filters.video | filters.document)
async def telegram_file_handler(client: Client, message: Message):
    """Handles video files uploaded directly to Telegram."""
    user_id = message.from_user.id
    
    if file_manager.is_banned(user_id):
        await message.reply_text("❌ You are permanently BANNED from using this bot.")
        return
        
    if file_manager.settings.get("maintenance", False) and user_id != Config.ADMIN_ID:
        await message.reply_text("⚙️ **Bot is under Maintenance!**\nBoss abhi bot par kuch kaam kar rahe hain. Thodi der baad try karein.")
        return

    media = message.video or message.document
    if not media:
        return

    if message.document and "video" not in (media.mime_type or ""):
        await message.reply_text("❌ This document does not look like a video.")
        return

    if media.file_size > Config.MAX_FILE_SIZE:
        await message.reply_text(
            f"❌ **Error: File is too large!**\n"
            f"Server crash hone se bachane ke liye maximum 2GB ki file allowed hai.\n"
            f"Aapki file: `{format_bytes(media.file_size)}`"
        )
        return

    if file_manager.is_user_locked(user_id):
        await message.reply_text("⚠️ You already have a process running. Please wait.")
        return
    
    file_manager.lock_user(user_id)
    status_msg = await message.reply_text("⏳ **Processing video...**\n_Please wait while I prepare the stream._")

    try:
        file_ext = mimetypes.guess_extension(media.mime_type) or ".mp4"
        filename = f"{uuid.uuid4()}{file_ext}"
        save_path = os.path.join(Config.STORAGE_DIR, filename)

        start_time = time.time()
        await message.download(
            file_name=save_path,
            progress=progress_bar,
            progress_args=(status_msg, start_time)
        )

        token = file_manager.add_video(user_id, save_path, media.mime_type)
        stream_link = f"{get_safe_base_url()}/watch/{token}"
        expiry_hours = file_manager.settings["expiry"] // 3600

        await status_msg.edit_text(
            f"✅ **Video Ready!**\n\n"
            f"📂 File: `{media.file_name or filename}`\n"
            f"💾 Size: `{format_bytes(media.file_size)}`\n"
            f"⏳ Expires in: {expiry_hours} Hours",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Watch Online", url=stream_link)]
            ])
        )

    except Exception as e:
        logger.error(f"Error handling Telegram file: {e}")
        await status_msg.edit_text(f"❌ **Error:** Failed to process video.\n`{str(e)}`")
        if 'save_path' in locals() and os.path.exists(save_path):
            os.remove(save_path)
            
    finally:
        file_manager.unlock_user(user_id)

@Client.on_message(filters.text & filters.regex(r"(https?://[^\s]+)"))
async def url_handler(client: Client, message: Message):
    """Handles direct video URLs."""
    user_id = message.from_user.id
    url = message.text.strip()

    if file_manager.is_banned(user_id):
        await message.reply_text("❌ You are permanently BANNED from using this bot.")
        return
        
    if file_manager.settings.get("maintenance", False) and user_id != Config.ADMIN_ID:
        await message.reply_text("⚙️ **Bot is under Maintenance!**\nBoss abhi bot par kuch kaam kar rahe hain. Thodi der baad try karein.")
        return

    if file_manager.is_user_locked(user_id):
        await message.reply_text("⚠️ You already have a process running. Please wait.")
        return

    file_manager.lock_user(user_id)
    status_msg = await message.reply_text("⏳ **Connecting to URL...**")

    save_path = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await status_msg.edit_text("❌ Error: Could not connect to URL.")
                    return
                
                content_type = response.headers.get('Content-Type', '')
                if 'video' not in content_type and 'application/octet-stream' not in content_type:
                     await status_msg.edit_text("❌ Error: The URL does not point to a valid video file.")
                     return

                filename = f"{uuid.uuid4()}.mp4" 
                save_path = os.path.join(Config.STORAGE_DIR, filename)
                
                total_size = int(response.headers.get('Content-Length', 0))
                
                if total_size > Config.MAX_FILE_SIZE:
                    await status_msg.edit_text("❌ **Error: File from URL is too large!** (Max 2GB)")
                    return

                downloaded = 0
                start_time = time.time()

                with open(save_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 1024): 
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            now = time.time()
                            if (now - start_time) > 5:
                                await status_msg.edit_text(f"📥 **Downloading URL...**\nSize: {format_bytes(downloaded)}")
                                start_time = now

        token = file_manager.add_video(user_id, save_path, "video/mp4")
        stream_link = f"{get_safe_base_url()}/watch/{token}"
        expiry_hours = file_manager.settings["expiry"] // 3600

        await status_msg.edit_text(
            f"✅ **URL Downloaded!**\n\n"
            f"⏳ Expires in: {expiry_hours} Hours",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Watch Online", url=stream_link)]
            ])
        )

    except Exception as e:
        logger.error(f"Error handling URL: {e}")
        await status_msg.edit_text(f"❌ **Error:** Failed to download URL.\n`{str(e)}`")
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
            
    finally:
        file_manager.unlock_user(user_id)

# --- THE HACKER BACKEND (Auto-Reply & Fetch) ---

@Client.on_message((filters.chat(Config.MAIN_CHANNEL_ID) | filters.private) & ~filters.command(["start", "stats", "settings", "ban", "unban"]))
async def channel_post_listener(client: Client, message: Message):
    """Main channel ya DM mein aane wale posts ko scan karega"""
    
    # Check karo ki message me inline buttons hain ya nahi
    if not getattr(message, "reply_markup", None) or not getattr(message.reply_markup, "inline_keyboard", None):
        return 
        
    mapping = {}
    
    # Smarter X-Ray: Ab strict DB ID ki jagah kisi bhi valid t.me link ko pakdega
    for row in message.reply_markup.inline_keyboard:
        for btn in row:
            if btn.url and ("t.me/c/" in btn.url or "t.me/" in btn.url):
                try:
                    # Link (e.g., t.me/c/123/317) me se aakhiri ka 317 (Message ID) nikalna
                    msg_id = int(btn.url.strip('/').split('/')[-1])
                    quality_text = btn.text.strip() # Button pe likha text (e.g., "720p")
                    mapping[quality_text] = msg_id 
                except ValueError:
                    continue
                    
    # Agar qualities mil gayi, toh Magic shuru!
    if mapping:
        post_id = file_manager.save_post_mapping(mapping)
        bot_info = await client.get_me()
        
        # Deep Link jo user ko DM me start karwayega
        deep_link = f"https://t.me/{bot_info.username}?start=watch_{post_id}"
        
        if message.chat.type == ChatType.PRIVATE:
            # Agar tumne DM me test karne ke liye forward kiya hai:
            await message.reply_text(
                "✅ **Post Scanned Successfully!** (Testing Mode)\nYe raha is post ka generated link:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Watch Online", url=deep_link)]
                ])
            )
        else:
            # Agar Main Channel mein Auto-Poster ne post daala hai:
            await message.reply_text(
                "🍿 **Stream This Episode Online**\n_Select your quality and watch instantly!_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Watch Online", url=deep_link)]
                ])
            )
