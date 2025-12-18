import os
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from search import get_google_images

# --- CONFIG (Environment Variables) ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token")
MONGO_URI = os.environ.get("MONGO_URI", "your_mongo_uri")
GOOGLE_KEY = os.environ.get("GOOGLE_KEY", "your_google_key")
CSE_ID = os.environ.get("CSE_ID", "your_cse_id")

# --- WEB SERVER FOR RENDER (Fixed Port Binding) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is Running!"

def run_web():
    # Render assigns a dynamic port, so we use os.environ.get
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- BOT SETUP ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database(MONGO_URI, "BotData")
scheduler = AsyncIOScheduler()

async def auto_post_task(chat_id):
    config = await db.get_settings(chat_id)
    query = "anime aesthetic pfps" if config['type'] == "anime" else "real aesthetic pfps"
    
    links = get_google_images(query, GOOGLE_KEY, CSE_ID)
    posted_count = 0
    
    for link in links:
        if posted_count >= int(config['count']):
            break
        if not await db.is_posted(link):
            try:
                await app.send_photo(chat_id, link, caption=f"✨ {config['type'].capitalize()} PFP")
                await db.save_post(link)
                posted_count += 1
                await asyncio.sleep(3) 
            except Exception as e:
                print(f"Error posting: {e}")
                continue

# --- HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    text = "👋 **Welcome!**\n\nMain Google se images fetch karke aapke channel par auto-post kar sakta hoon.\n\nBot ko channel mein **Admin** banayein aur niche settings set karein."
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")]])
    await message.reply_text(text, reply_markup=btn)

@app.on_callback_query()
async def handle_callbacks(client, cb):
    chat_id = cb.message.chat.id
    data = cb.data

    if data == "open_settings":
        conf = await db.get_settings(chat_id)
        text = (f"⚙️ **Bot Settings**\n\n"
                f"🖼 **Type:** {conf['type'].capitalize()}\n"
                f"🔢 **Post Count:** {conf['count']} photo(s)\n"
                f"⏰ **Interval:** {conf['interval']} minutes")
        
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼 Toggle Type", callback_data="toggle_type")],
            [InlineKeyboardButton("🔢 1 Photo", callback_data="set_1"), InlineKeyboardButton("🔢 5 Photos", callback_data="set_5")],
            [InlineKeyboardButton("⏰ 30 Min", callback_data="int_30"), InlineKeyboardButton("⏰ 1 Hour", callback_data="int_60")],
            [InlineKeyboardButton("🚀 Start Auto-Post", callback_data="start_bot")]
        ])
        await cb.edit_message_text(text, reply_markup=btns)

    elif data == "toggle_type":
        conf = await db.get_settings(chat_id)
        new_type = "real" if conf.get('type') == "anime" else "anime"
        await db.update_settings(chat_id, "type", new_type)
        await handle_callbacks(client, cb)

    elif data.startswith("set_"):
        count = int(data.split("_")[1])
        await db.update_settings(chat_id, "count", count)
        await handle_callbacks(client, cb)

    elif data.startswith("int_"):
        interval = int(data.split("_")[1])
        await db.update_settings(chat_id, "interval", interval)
        await handle_callbacks(client, cb)

    elif data == "start_bot":
        conf = await db.get_settings(chat_id)
        scheduler.add_job(
            auto_post_task, 
            "interval", 
            minutes=int(conf['interval']), 
            args=[chat_id], 
            id=str(chat_id), 
            replace_existing=True
        )
        await cb.answer("✅ Auto-posting started for this chat!", show_alert=True)

# --- EXECUTION ---
if __name__ == "__main__":
    # Start Web Server in a separate thread
    server_thread = Thread(target=run_web)
    server_thread.daemon = True
    server_thread.start()
    
    # Start Scheduler
    if not scheduler.running:
        scheduler.start()
    
    # Run Bot
    app.run()
    
