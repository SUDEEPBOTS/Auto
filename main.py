import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from search import get_google_images

# --- CONFIG ---
API_ID = 12345 
API_HASH = "your_hash"
BOT_TOKEN = "your_token"
MONGO_URI = "your_mongo_uri"
GOOGLE_KEY = "your_google_key"
CSE_ID = "your_cse_id"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database(MONGO_URI, "BotData")
scheduler = AsyncIOScheduler()

async def auto_post_task(chat_id):
    config = await db.get_settings(chat_id)
    query = "anime aesthetic pfp" if config['type'] == "anime" else "luxury aesthetic pfp"
    
    links = get_google_images(query, GOOGLE_KEY, CSE_ID)
    posted_count = 0
    
    for link in links:
        if posted_count >= config['count']: break
        if not await db.is_posted(link):
            try:
                await app.send_photo(chat_id, link)
                await db.save_post(link)
                posted_count += 1
            except: continue

@app.on_message(filters.command("start"))
async def start(client, message):
    text = "👋 Welcome! Main Auto-Post Bot hoon.\nNiche diye button se settings manage karein."
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")]])
    await message.reply_text(text, reply_markup=btn)

@app.on_callback_query()
async def handle_callbacks(client, cb):
    chat_id = cb.message.chat.id
    data = cb.data

    if data == "open_settings":
        conf = await db.get_settings(chat_id)
        text = f"⚙️ **Settings**\n\nType: {conf['type']}\nPost Count: {conf['count']}\nInterval: {conf['interval']} min"
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("Change Type (Anime/Real)", callback_data="toggle_type")],
            [InlineKeyboardButton("Set 1 Photo", callback_data="set_1"), InlineKeyboardButton("Set 3 Photos", callback_data="set_3")],
            [InlineKeyboardButton("🚀 Start Posting", callback_data="start_bot")]
        ])
        await cb.edit_message_text(text, reply_markup=btns)

    elif data == "toggle_type":
        conf = await db.get_settings(chat_id)
        new_type = "real" if conf['type'] == "anime" else "anime"
        await db.update_settings(chat_id, "type", new_type)
        await cb.answer(f"Switched to {new_type}")
        # Refresh menu
        await handle_callbacks(client, cb)

    elif data == "start_bot":
        conf = await db.get_settings(chat_id)
        scheduler.add_job(auto_post_task, "interval", minutes=conf['interval'], args=[chat_id], id=str(chat_id), replace_existing=True)
        await cb.answer("Auto-post scheduled!", show_alert=True)

if __name__ == "__main__":
    scheduler.start()
    app.run()
  
