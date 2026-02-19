import os
import time
import uuid
import logging
import aiohttp
import mimetypes
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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

async def progress_bar(current, total, status_msg, start_time):
    """Updates the progress message during download."""
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = get_readable_time(elapsed_time / 1000)
        estimated_total_time = get_readable_time(estimated_total_time / 1000)

        try:
            await status_msg.edit_text(
                f"📥 **Downloading...**\n"
                f"📊 Progress: {percentage:.2f}%\n"
                f"🚀 Speed: {get_readable_time(speed)}/s\n"
                f"⏳ ETA: {estimated_total_time}"
            )
        except Exception:
            pass

# --- Handlers ---

@Client.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply_text(
        "👋 **Hello! I am a Video Streaming Bot.**\n\n"
        "📤 **Send me a video file** or a **direct download link**.\n"
        "🔗 I will generate a temporary public streaming link for you.\n\n"
        "⚠️ _Links expire in 24 hours._"
    )

@Client.on_message(filters.video | filters.document)
async def telegram_file_handler(client: Client, message: Message):
    """Handles video files uploaded directly to Telegram."""
    user_id = message.from_user.id
    
    # 1. Filter Check
    media = message.video or message.document
    if not media:
        return

    # Basic MIME check for documents
    if message.document and "video" not in (media.mime_type or ""):
        await message.reply_text("❌ This document does not look like a video.")
        return

    # 2. Concurrency Check
    if file_manager.is_user_locked(user_id):
        await message.reply_text("⚠️ You already have a process running. Please wait.")
        return
    
    file_manager.lock_user(user_id)
    status_msg = await message.reply_text("⏳ **Processing video...**\n_Please wait while I prepare the stream._")

    try:
        # 3. Download
        file_ext = mimetypes.guess_extension(media.mime_type) or ".mp4"
        filename = f"{uuid.uuid4()}{file_ext}"
        save_path = os.path.join(Config.STORAGE_DIR, filename)

        start_time = time.time()
        await message.download(
            file_name=save_path,
            progress=progress_bar,
            progress_args=(status_msg, start_time)
        )

        # 4. Generate Link
        token = file_manager.add_video(user_id, save_path, media.mime_type)
        stream_link = f"{Config.BASE_URL}/watch/{token}"

        await status_msg.edit_text(
            f"✅ **Video Ready!**\n\n"
            f"📂 File: `{media.file_name or filename}`\n"
            f"💾 Size: `{get_readable_time(media.file_size)}`\n"
            f"⏳ Expires in: 24 Hours",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Watch Online", url=stream_link)]
            ])
        )

    except Exception as e:
        logger.error(f"Error handling Telegram file: {e}")
        await status_msg.edit_text(f"❌ **Error:** Failed to process video.\n`{str(e)}`")
        # Cleanup if failed
        if 'save_path' in locals() and os.path.exists(save_path):
            os.remove(save_path)
            
    finally:
        file_manager.unlock_user(user_id)

@Client.on_message(filters.text & filters.regex(r"(https?://[^\s]+)"))
async def url_handler(client: Client, message: Message):
    """Handles direct video URLs."""
    user_id = message.from_user.id
    url = message.text.strip()

    if file_manager.is_user_locked(user_id):
        await message.reply_text("⚠️ You already have a process running. Please wait.")
        return

    file_manager.lock_user(user_id)
    status_msg = await message.reply_text("⏳ **Connecting to URL...**")

    save_path = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # 1. Validation
                if response.status != 200:
                    await status_msg.edit_text("❌ Error: Could not connect to URL.")
                    return
                
                content_type = response.headers.get('Content-Type', '')
                if 'video' not in content_type and 'application/octet-stream' not in content_type:
                     await status_msg.edit_text("❌ Error: The URL does not point to a valid video file.")
                     return

                # 2. Prepare Path
                filename = f"{uuid.uuid4()}.mp4" # Default to mp4 if unknown
                save_path = os.path.join(Config.STORAGE_DIR, filename)
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                start_time = time.time()

                # 3. Stream Download
                with open(save_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 1024): # 1MB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every few seconds
                        if total_size > 0:
                            now = time.time()
                            if (now - start_time) > 5: # Update every 5s to avoid spam
                                # (Simplified progress logic for brevity in URL handler)
                                await status_msg.edit_text(f"📥 **Downloading URL...**\nSize: {downloaded // (1024*1024)} MB")
                                start_time = now

        # 4. Generate Link
        token = file_manager.add_video(user_id, save_path, "video/mp4")
        stream_link = f"{Config.BASE_URL}/watch/{token}"

        await status_msg.edit_text(
            f"✅ **URL Downloaded!**\n\n"
            f"⏳ Expires in: 24 Hours",
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