import asyncio
import importlib

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from VenomX import LOGGER, app, userbot
from VenomX.core.call import Ayush
from VenomX.misc import sudo
from VenomX.plugins import ALL_MODULES
from VenomX.utils.database import get_banned_users, get_gbanned
from VenomX.utils.cookie_handler import fetch_and_store_cookies
from config import BANNED_USERS


async def load_banned_users():
    try:
        gbanned_users = await get_gbanned()
        if gbanned_users:
            for user_id in gbanned_users:
                BANNED_USERS.add(user_id)
            LOGGER("VenomX").info(f"🚫 Loaded {len(gbanned_users)} globally banned users")
        banned_users = await get_banned_users()
        if banned_users:
            new_bans = 0
            for user_id in banned_users:
                if user_id not in BANNED_USERS:
                    BANNED_USERS.add(user_id)
                    new_bans += 1
            if new_bans > 0:
                LOGGER("VenomX").info(f"🚫 Loaded {new_bans} additional banned users")
        total_banned = len(BANNED_USERS)
        if total_banned > 0:
            LOGGER("VenomX").info(f"🛡️ Total banned users in memory: {total_banned}")
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Failed to load banned users: {e}")


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("⚠️ Activation Failed - Assistant sessions are missing.")
        exit()

    try:
        await fetch_and_store_cookies()
        LOGGER("VenomX").info("🍪 Cookies Integrated - Y-t music stream ready.")
    except Exception as e:
        LOGGER("VenomX").warning(f"☁️ Cookie Warning - {e}")

    await sudo()

    await load_banned_users()

    try:
        await app.start()
        LOGGER("VenomX").info("🚀 Bot client started successfully")
    except Exception as e:
        LOGGER("VenomX").error(f"❌ Failed to start bot client: {e}")
        exit()

    try:
        for all_module in ALL_MODULES:
            importlib.import_module("VenomX.plugins" + all_module)
        LOGGER("VenomX.plugins").info("🧩 Module Constellation - All systems synced.")
    except Exception as e:
        LOGGER("VenomX").error(f"❌ Failed to load plugins: {e}")
        exit()

    try:
        await userbot.start()
        LOGGER("VenomX").info("👤 Userbot started successfully")
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Userbot start failed: {e}")

    try:
        await Ayush.start()
        LOGGER("VenomX").info("🎵 Voice system initialized")
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Voice system failed: {e}")

    try:
        await Ayush.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
        LOGGER("VenomX").info("📡 Voice stream test successful")
    except NoActiveGroupCall:
        LOGGER("VenomX").error(
            "🔇 No Active VC - Log Group voice chat is dormant.\n"
            "💀 Aborting Launch..."
        )
        exit()
    except Exception as e:
        LOGGER("VenomX").warning(f"📡 Voice stream test warning: {e}")

    try:
        await Ayush.decorators()
        LOGGER("VenomX").info(
            "⚡ Online - VenomX music sequence activated.\n"
            "☁️ Part of VenomX Project."
        )
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Decorators failed: {e}")

    try:
        await idle()
    except KeyboardInterrupt:
        LOGGER("VenomX").info("🛑 Received stop signal")
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Idle loop error: {e}")
    finally:
        try:
            await app.stop()
            LOGGER("VenomX").info("🤖 Bot client stopped")
        except:
            pass
        try:
            await userbot.stop()
            LOGGER("VenomX").info("👤 Userbot stopped")
        except:
            pass
        LOGGER("VenomX").info("🌩️ Cycle Closed - VenomX sleeps.")


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(init())
    except KeyboardInterrupt:
        LOGGER("VenomX").info("🛑 Bot stopped by user")
    except Exception as e:
        LOGGER("VenomX").error(f"💥 Critical error: {e}")
