import os
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from search import get_google_images

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token")
MONGO_URI = os.environ.get("MONGO_URI", "your_mongo_uri")
GOOGLE_KEY = os.environ.get("GOOGLE_KEY", "your_google_key")
CSE_ID = os.environ.get("CSE_ID", "your_cse_id")

# --- WEB SERVER ---
web_app = Flask('')
@web_app.route('/')
def home(): return "Bot is Alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- BOT & SCHEDULER SETUP ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database(MONGO_URI, "BotData")
scheduler = AsyncIOScheduler()

async def auto_post_task(chat_id):
    config = await db.get_settings(chat_id)
    query = "anime aesthetic pfps" if config['type'] == "anime" else "real aesthetic pfps"
    links = get_google_images(query, GOOGLE_KEY, CSE_ID)
    
    posted_count = 0
    for link in links:
        if posted_count >= int(config['count']): break
        if not await db.is_posted(link):
            try:
                await app.send_photo(chat_id, link, caption=f"✨ {config['type'].capitalize()} PFP")
                await db.save_post(link)
                posted_count += 1
                await asyncio.sleep(3)
            except: continue

# --- HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")]])
    await message.reply_text("👋 Welcome! Use settings to configure auto-post.", reply_markup=btn)

@app.on_callback_query()
async def handle_callbacks(client, cb):
    chat_id = cb.message.chat.id
    if cb.data == "open_settings":
        conf = await db.get_settings(chat_id)
        text = f"⚙️ **Settings**\n\nType: {conf['type']}\nInterval: {conf['interval']} min"
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼 Toggle Type", callback_data="toggle_type")],
            [InlineKeyboardButton("🚀 Start Auto-Post", callback_data="start_bot")]
        ])
        await cb.edit_message_text(text, reply_markup=btns)
    
    elif cb.data == "toggle_type":
        conf = await db.get_settings(chat_id)
        new_type = "real" if conf.get('type') == "anime" else "anime"
        await db.update_settings(chat_id, "type", new_type)
        await handle_callbacks(client, cb)

    elif cb.data == "start_bot":
        conf = await db.get_settings(chat_id)
        scheduler.add_job(auto_post_task, "interval", minutes=int(conf['interval']), args=[chat_id], id=str(chat_id), replace_existing=True)
        await cb.answer("✅ Started!", show_alert=True)

# --- MAIN RUNNER (Fixed) ---
async def main():
    # Start Flask in thread
    Thread(target=run_web, daemon=True).start()
    
    # Start Bot client
    await app.start()
    
    # Start Scheduler after loop is running
    scheduler.start()
    
    print("Bot is Online and Scheduler Started!")
    await idle() # Keeps the bot running
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
