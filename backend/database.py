from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=2000)

database = client.mt5_tracker
trade_collection = database.get_collection("trades")
daily_summary_collection = database.get_collection("daily_summaries")
