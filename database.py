from motor.motor_asyncio import AsyncIOMotorClient

class Database:
    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.settings = self.db["settings"]
        self.history = self.db["history"]

    async def get_settings(self, chat_id):
        user = await self.settings.find_one({"chat_id": chat_id})
        return user or {"chat_id": chat_id, "type": "anime", "count": 1, "interval": 60}

    async def update_settings(self, chat_id, key, value):
        await self.settings.update_one(
            {"chat_id": chat_id}, {"$set": {key: value}}, upsert=True
        )

    async def is_posted(self, url):
        return await self.history.find_one({"url": url}) is not None

    async def save_post(self, url):
        await self.history.insert_one({"url": url})
      
