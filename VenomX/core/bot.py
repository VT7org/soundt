# uvloop for faster event loop performance
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import sys
import traceback
from typing import Any

from pyrogram import Client, errors
from pyrogram.enums import ChatMemberStatus, ParseMode

import config
from ..logging import LOGGER


def _valid_logger_id(val: Any) -> bool:
    """Quick sanity check for LOGGER_ID (int or non-empty str)."""
    if val is None:
        return False
    if isinstance(val, int):
        return True
    if isinstance(val, str) and val.strip() != "":
        return True
    return False


class AyuBot(Client):
    def __init__(self):
        super().__init__(
            name="BillaMusic",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            in_memory=True,
            workers=30,
            max_concurrent_transmissions=7,
            parse_mode=ParseMode.HTML,  # Ensures safe HTML parsing
        )
        LOGGER(__name__).info("🧠 Oᴘᴜs ᴀssɪsᴛᴀɴᴛ ᴇɴɢɪɴᴇ ɪɴɪᴛɪᴀʟɪᴢᴇᴅ...")

    async def start(self):
        await super().start()

        me = await self.get_me()
        self.username, self.id = me.username, me.id
        self.name = f"{me.first_name} {me.last_name or ''}".strip()
        self.mention = me.mention

        # notify logger chat if configured — but be defensive and non-fatal
        logger_id = getattr(config, "LOGGER_ID", None)
        if not _valid_logger_id(logger_id):
            LOGGER(__name__).warning("⚠️ LOGGER_ID not set or invalid; skipping startup notification.")
        else:
            try:
                await self.send_message(
                    logger_id,
                    (
                        f"<b> Bᴏᴛ ɪs ʀᴇᴀᴅʏ</b>\n\n"
                        f"• ɴᴀᴍᴇ : {self.name}\n"
                        f"• ᴜsᴇʀɴᴀᴍᴇ : @{self.username}\n"
                        f"• ɪᴅ : <code>{self.id}</code>"
                    ),
                )
                LOGGER(__name__).info("✅ Startup notification sent to LOGGER_ID")
            except (errors.ChannelInvalid, errors.PeerIdInvalid) as e:
                # these are configuration/user errors — log and continue (don't exit)
                LOGGER(__name__).error(
                    "🚫 LOGGER chat not accessible or invalid. Add the bot to the logger chat and promote it if needed."
                )
                LOGGER(__name__).debug(traceback.format_exc())
            except ValueError as ve:
                # matches your log: record details but keep process alive
                LOGGER(__name__).error(f"❌ Failed to send startup notification: ValueError: {ve}")
                LOGGER(__name__).debug(traceback.format_exc())
            except Exception as exc:
                # unexpected — log full traceback but continue
                LOGGER(__name__).error(
                    f"❌ Failed to send startup notification: {type(exc).__name__}"
                )
                LOGGER(__name__).debug(traceback.format_exc())

        # Check admin status in the logger chat only if logger_id looks like a chat id/username and previous send didn't fail fatally
        if _valid_logger_id(logger_id):
            try:
                member = await self.get_chat_member(logger_id, self.id)
                if member.status != ChatMemberStatus.ADMINISTRATOR:
                    LOGGER(__name__).warning(
                        "⚠️ Bot is not an administrator in LOGGER chat — reports may fail. Promote the bot if you expect reports."
                    )
                else:
                    LOGGER(__name__).info("✅ Bot is administrator in LOGGER chat")
            except errors.ChatAdminRequired:
                LOGGER(__name__).warning("⚠️ Bot lacks permissions to check admin status in LOGGER chat.")
                LOGGER(__name__).debug(traceback.format_exc())
            except (errors.UserNotParticipant, errors.PeerIdInvalid, errors.ChannelInvalid) as e:
                LOGGER(__name__).warning(
                    "⚠️ Could not verify admin status in LOGGER chat (not a participant / invalid chat)."
                )
                LOGGER(__name__).debug(traceback.format_exc())
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ Error checking admin status: {e}")
                LOGGER(__name__).debug(traceback.format_exc())

        LOGGER(__name__).info(f"🎧 Oᴘᴜs ʙᴏᴛ ʟᴀᴜɴᴄʜᴇᴅ ᴀs {self.name} (@{self.username})")
