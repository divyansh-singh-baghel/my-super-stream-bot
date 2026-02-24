import shutil
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from modules.file_manager import file_manager

# 🛡️ Security Guard: Sirf ADMIN_ID wale (yani tum) hi ye commands use kar payenge
admin_filter = filters.user(Config.ADMIN_ID)

# --- 1. ADVANCED STATS (/stats) ---
@Client.on_message(filters.command("stats") & admin_filter)
async def stats_command(client: Client, message: Message):
    # Server ki memory check karna
    total, used, free = shutil.disk_usage(".")
    total_gb = total / (1024**3)
    used_gb = used / (1024**3)
    free_gb = free / (1024**3)
    
    top_users = file_manager.get_top_users()
    total_links = len(file_manager.videos)
    
    stats_text = (
        "📊 **Boss Mode - Live Stats**\n\n"
        f"💾 **Server Storage:** `{used_gb:.2f} GB` used out of `{total_gb:.2f} GB`\n"
        f"🟢 **Free Space:** `{free_gb:.2f} GB`\n"
        f"🔗 **Active Stream Links:** `{total_links}`\n\n"
        f"🏆 **Top Users (Spam Tracker):**\n{top_users}"
    )
    await message.reply_text(stats_text)

# --- 2. BAN SYSTEM (/ban & /unban) ---
@Client.on_message(filters.command("ban") & admin_filter)
async def ban_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Sahi format: `/ban user_id`")
    try:
        user_id = int(message.command[1])
        file_manager.ban_user(user_id)
        await message.reply_text(f"✅ **BANNED:** User `{user_id}` ab is bot ko use nahi kar payega.")
    except ValueError:
        await message.reply_text("❌ Invalid User ID.")

@Client.on_message(filters.command("unban") & admin_filter)
async def unban_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Sahi format: `/unban user_id`")
    try:
        user_id = int(message.command[1])
        file_manager.unban_user(user_id)
        await message.reply_text(f"✅ **UNBANNED:** User `{user_id}` ko maaf kar diya gaya hai.")
    except ValueError:
        await message.reply_text("❌ Invalid User ID.")

# --- 3. DYNAMIC SETTINGS PANEL (/settings) ---
@Client.on_message(filters.command("settings") & admin_filter)
async def settings_command(client: Client, message: Message):
    await send_settings_menu(message)

async def send_settings_menu(message: Message | CallbackQuery):
    is_maint = file_manager.settings["maintenance"]
    expiry_hours = file_manager.settings["expiry"] // 3600

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Maintenance Mode: {'🔴 ON (Locked)' if is_maint else '🟢 OFF (Open)'}", callback_data="toggle_maint")],
        [InlineKeyboardButton(f"⏳ File Expiry Time: {expiry_hours} Hours", callback_data="change_expiry")]
    ])
    
    text = "⚙️ **Admin Settings Panel**\nYahan se bot control karo bina code touch kiye:"
    
    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=keyboard)
    else:
        await message.message.edit_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("toggle_maint") | filters.regex("change_expiry"))
async def settings_callback(client: Client, query: CallbackQuery):
    if query.from_user.id != Config.ADMIN_ID:
        return await query.answer("❌ You are not the Boss!", show_alert=True)
        
    if query.data == "toggle_maint":
        file_manager.settings["maintenance"] = not file_manager.settings["maintenance"]
        await query.answer("Maintenance mode updated!")
        await send_settings_menu(query)
        
    elif query.data == "change_expiry":
        current = file_manager.settings["expiry"] // 3600
        # Time cycle: 12 ghante -> 24 ghante -> 48 ghante
        if current == 12: new_hours = 24
        elif current == 24: new_hours = 48
        else: new_hours = 12
        
        file_manager.settings["expiry"] = new_hours * 3600
        await query.answer(f"Expiry time set to {new_hours} hours!")
        await send_settings_menu(query)
