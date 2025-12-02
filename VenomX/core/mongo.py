from motor.motor_asyncio import AsyncIOMotorClient as _mongo_client_
from pymongo import MongoClient
from pyrogram import Client
import config
from ..logging import LOGGER

# Default fallback MongoDB URI (used only if config.MONGO_DB_URI is missing or invalid)
TEMP_MONGODB = "mongodb+srv://strvortexcore:vortexcore0019@cluster0.fkb3o.mongodb.net/?retryWrites=true&w=majority"

# Choose which Mongo URI to use
MONGO_URI = getattr(config, "MONGO_DB_URI", "").strip() or TEMP_MONGODB

if MONGO_URI == TEMP_MONGODB:
    LOGGER(__name__).warning("⚠️ No Mongo URI found in config — using temporary fallback database.")
else:
    LOGGER(__name__).info("✅ Using Mongo URI from config.")

# Create clients
try:
    _mongo_async_ = _mongo_client_(MONGO_URI)
    _mongo_sync_ = MongoClient(MONGO_URI)
except Exception as e:
    LOGGER(__name__).error(f"❌ Failed to connect to MongoDB: {e}")
    raise e

# Select default database (always 'OpusV')
mongodb = _mongo_async_["OpusV"]
pymongodb = _mongo_sync_["OpusV"]

# Optional: log which DB is active
LOGGER(__name__).info("📦 MongoDB connection established to database: OpusV")

# If fallback is used, connect bot just for username info (non-critical)
if MONGO_URI == TEMP_MONGODB:
    try:
        temp_client = Client(
            "OpusV",
            bot_token=config.BOT_TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
        )
        temp_client.start()
        info = temp_client.get_me()
        LOGGER(__name__).info(f"🧩 Temporary Mongo session active for @{info.username}")
        temp_client.stop()
    except Exception as e:
        LOGGER(__name__).warning(f"⚠️ Could not verify bot username for temp DB: {e}")
