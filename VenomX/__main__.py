import asyncio
import importlib
import inspect
import traceback
import os
import sys

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
import VenomX as _venom_pkg
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


def log_startup_paths():
    try:
        LOGGER("VenomX").info("Startup info:")
        LOGGER("VenomX").info(f" CWD: {os.getcwd()}")
        LOGGER("VenomX").info(f" Python executable: {sys.executable}")
        LOGGER("VenomX").info(f" sys.path[0:5]: {sys.path[:5]}")
    except Exception:
        pass
    try:
        cfg_file = getattr(config, "__file__", None)
        LOGGER("VenomX").info(f" Config module file: {cfg_file}")
    except Exception:
        pass
    try:
        LOGGER("VenomX").info(f" VenomX package file: {getattr(_venom_pkg, '__file__', None)}")
    except Exception:
        pass
    try:
        sessions_count = 0
        for name in ("STRING1", "STRING2", "STRING3", "STRING4", "STRING5"):
            if getattr(config, name, None):
                sessions_count += 1
        # fallback for older config layout
        if hasattr(config, "STRING_SESSIONS"):
            try:
                sessions_count = len(getattr(config, "STRING_SESSIONS") or [])
            except Exception:
                pass
        LOGGER("VenomX").info(f" Assistant session count (approx): {sessions_count}")
    except Exception:
        pass
    try:
        LOGGER("VenomX").info(f" Plugin/module count: {len(ALL_MODULES)}")
    except Exception:
        pass


async def safe_notify_startup():
    """
    Try to call any startup notification function defined in VenomX.core.bot.
    This protects against ValueError or other exceptions that may occur when
    the bot attempts to send a notification (e.g., invalid chat id).
    """
    try:
        bot_mod = importlib.import_module("VenomX.core.bot")
    except Exception:
        # no bot module or failed import — nothing to notify
        return

    # candidate function names that projects commonly use
    candidates = [
        "send_startup_notification",
        "send_startup",
        "notify_startup",
        "announce_startup",
        "startup_notify",
    ]
    for name in candidates:
        fn = getattr(bot_mod, name, None)
        if callable(fn):
            try:
                result = fn()
                if inspect.isawaitable(result):
                    await result
                LOGGER("VenomX").info(f"✅ Called startup notifier: {name}")
            except ValueError as ve:
                # This mirrors your logs: catch and log ValueError specifically and continue
                LOGGER("VenomX.core.bot").error(f"❌ Failed to send startup notification: {ve}")
                LOGGER("VenomX.core.bot").error(traceback.format_exc())
            except Exception as e:
                LOGGER("VenomX.core.bot").warning(f"⚠️ Startup notifier '{name}' raised: {e}")
                LOGGER("VenomX.core.bot").warning(traceback.format_exc())
            finally:
                # whether success or not, don't try other names after a callable was found
                return


async def init():
    log_startup_paths()

    if (
        not getattr(config, "STRING1", None)
        and not getattr(config, "STRING2", None)
        and not getattr(config, "STRING3", None)
        and not getattr(config, "STRING4", None)
        and not getattr(config, "STRING5", None)
    ):
        # also accept STRING_SESSIONS list if present
        if not getattr(config, "STRING_SESSIONS", None):
            LOGGER("VenomX").error("⚠️ Activation Failed - Assistant sessions are missing.")
            return

    try:
        await fetch_and_store_cookies()
        LOGGER("VenomX").info("🍪 Cookies integrated")
    except Exception as e:
        LOGGER("VenomX").warning(f"☁️ Cookie warning: {e}")

    # --- SAFELY CALL sudo (sync or async) ---
    try:
        if sudo is None:
            LOGGER("VenomX").warning("⚠️ 'sudo' is not defined in VenomX.misc; skipping sudo step.")
        elif inspect.iscoroutinefunction(sudo):
            await sudo()
            LOGGER("VenomX").info("✅ sudo coroutine executed")
        elif callable(sudo):
            maybe = sudo()
            if inspect.isawaitable(maybe):
                await maybe
                LOGGER("VenomX").info("✅ awaited returned awaitable from sudo()")
            else:
                LOGGER("VenomX").info("✅ sudo() executed (sync)")
        else:
            LOGGER("VenomX").warning("⚠️ 'sudo' exists but is not callable; skipping sudo step.")
    except Exception as e:
        LOGGER("VenomX").warning(f"⚠️ sudo step failed: {e}")

    await load_banned_users()

    try:
        await app.start()
        LOGGER("VenomX").info("🚀 Bot client started")
    except Exception as e:
        LOGGER("VenomX").error(f"❌ Failed to start bot client: {e}")
        return

    # Attempt startup notification but protect from ValueError or other send errors
    try:
        await safe_notify_startup()
    except Exception as e:
        # safe_notify_startup already logs traceback for inner errors, but be defensive
        LOGGER("VenomX.core.bot").warning(f"⚠️ safe_notify_startup failed: {e}")
        LOGGER("VenomX.core.bot").warning(traceback.format_exc())

    try:
        for module_path in ALL_MODULES:
            importlib.import_module(module_path)
        LOGGER("VenomX.plugins").info("🧩 Modules imported")
    except Exception as e:
        LOGGER("VenomX").error(f"❌ Failed to load plugins: {e}")
        try:
            await app.stop()
        except:
            pass
        return

    try:
        await userbot.start()
        LOGGER("VenomX").info("👤 Userbot started")
    except Exception as e:
        LOGGER("VenomX").warning(f"⚠️ Userbot start failed: {e}")

    try:
        await Ayush.start()
        LOGGER("VenomX").info("🎵 Voice system initialized")
    except Exception as e:
        LOGGER("VenomX").error(f"⚠️ Voice system failed: {e}")

    try:
        await Ayush.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
        LOGGER("VenomX").info("📡 Voice stream test successful")
    except NoActiveGroupCall:
        LOGGER("VenomX").error("🔇 No Active VC - Log Group voice chat is dormant. Aborting.")
        try:
            await app.stop()
        except:
            pass
        try:
            await userbot.stop()
        except:
            pass
        return
    except Exception as e:
        LOGGER("VenomX").warning(f"📡 Voice stream test warning: {e}")

    try:
        await Ayush.decorators()
        LOGGER("VenomX").info("⚡ VenomX music sequence activated")
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
        except:
            pass
        try:
            await userbot.stop()
        except:
            pass
        try:
            await Ayush.stop()
        except:
            pass
        LOGGER("VenomX").info("🌩️ VenomX stopped")


if __name__ == "__main__":
    try:
        # Keep compatibility with uvloop while using existing run_until_complete entry point
        asyncio.get_event_loop().run_until_complete(init())
    except KeyboardInterrupt:
        LOGGER("VenomX").info("🛑 Bot stopped by user")
    except Exception:
        LOGGER("VenomX").error("💥 Critical error:\n" + traceback.format_exc())
