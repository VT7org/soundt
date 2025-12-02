import asyncio
import time

from py_yt import VideosSearch
from pyrogram import filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram.errors import BadRequest

import config
from config import BANNED_USERS, START_IMG_URL
from config.config import OWNER_ID
from strings import command, get_string
from VenomX import Platform, app
from VenomX.misc import SUDOERS, _boot_
from VenomX.plugins.bot.help import paginate_modules
from VenomX.plugins.play.playlist import del_plist_msg
from VenomX.plugins.sudo.sudoers import sudoers_list
from VenomX.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_assistant,
    get_lang,
    get_userss,
    is_on_off,
    is_served_private_chat,
)
from VenomX.utils.decorators.language import LanguageStart
from VenomX.utils.formatters import get_readable_time
from VenomX.utils.functions import MARKDOWN, WELCOMEHELP
from VenomX.utils.inline import private_panel, start_pannel

loop = asyncio.get_running_loop()


def sanitize_markup(markup):
    if not markup:
        return None
    if isinstance(markup, InlineKeyboardMarkup):
        rows = markup.inline_keyboard
    elif isinstance(markup, list):
        rows = markup
    else:
        return None
    out_rows = []
    for row in rows:
        kept = []
        for btn in row:
            url = getattr(btn, "url", None) or ""
            user_id = getattr(btn, "user_id", None)
            if user_id:
                continue
            if isinstance(url, str) and url.startswith("tg://user"):
                continue
            new_btn = InlineKeyboardButton(
                text=getattr(btn, "text", "") or "",
                url=getattr(btn, "url", None),
                callback_data=getattr(btn, "callback_data", None),
                switch_inline_query=getattr(btn, "switch_inline_query", None),
                switch_inline_query_current_chat=getattr(btn, "switch_inline_query_current_chat", None),
                login_url=getattr(btn, "login_url", None),
                pay=getattr(btn, "pay", None),
            )
            kept.append(new_btn)
        if kept:
            out_rows.append(kept)
    if not out_rows:
        return None
    return InlineKeyboardMarkup(out_rows)


async def _try_send(coro, fallback_coro=None):
    try:
        return await coro
    except BadRequest as e:
        err = str(e).lower()
        if "button_user_privacy_restricted" in err or "button" in err:
            if fallback_coro:
                return await fallback_coro
            return None
        raise


async def safe_reply_photo(message: Message, photo, caption=None, parse_mode=None, reply_markup=None):
    mk = sanitize_markup(reply_markup)
    if mk:
        res = await _try_send(message.reply_photo(photo=photo, caption=caption, reply_markup=mk, parse_mode=parse_mode),
                              fallback_coro=message.reply_photo(photo=photo, caption=caption, parse_mode=parse_mode))
        return res
    return await _try_send(message.reply_photo(photo=photo, caption=caption, parse_mode=parse_mode))


async def safe_reply_text(message: Message, text, parse_mode=None, reply_markup=None, disable_web_page_preview=False):
    mk = sanitize_markup(reply_markup)
    if mk:
        res = await _try_send(message.reply_text(text=text, parse_mode=parse_mode, reply_markup=mk, disable_web_page_preview=disable_web_page_preview),
                              fallback_coro=message.reply_text(text=text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview))
        return res
    return await _try_send(message.reply_text(text=text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview))


async def safe_send_photo(chat_id, photo, caption=None, parse_mode=None, reply_markup=None):
    mk = sanitize_markup(reply_markup)
    if mk:
        res = await _try_send(app.send_photo(chat_id, photo=photo, caption=caption, parse_mode=parse_mode, reply_markup=mk),
                              fallback_coro=app.send_photo(chat_id, photo=photo, caption=caption, parse_mode=parse_mode))
        return res
    return await _try_send(app.send_photo(chat_id, photo=photo, caption=caption, parse_mode=parse_mode))


async def safe_send_message(chat_id, text, parse_mode=None, reply_markup=None):
    mk = sanitize_markup(reply_markup)
    if mk:
        res = await _try_send(app.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=mk),
                              fallback_coro=app.send_message(chat_id, text, parse_mode=parse_mode))
        return res
    return await _try_send(app.send_message(chat_id, text, parse_mode=parse_mode))


@app.on_message(command("START_COMMAND") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_comm(client, message: Message, _):
    chat_id = message.chat.id
    await add_served_user(message.from_user.id)
    parts = message.text.split(None, 1)
    if len(parts) > 1:
        name = parts[1]
        if name.startswith("help"):
            keyboard = await paginate_modules(0, chat_id, close=True)
            if START_IMG_URL:
                return await safe_reply_photo(message, photo=START_IMG_URL, caption=_["help_1"], reply_markup=keyboard)
            return await safe_reply_text(message, text=_["help_1"], reply_markup=keyboard)
        if name.startswith("song"):
            await safe_reply_text(message, _["song_2"])
            return
        if name == "mkdwn_help":
            await safe_reply_text(message, MARKDOWN, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            return
        if name == "greetings":
            await safe_reply_text(message, WELCOMEHELP, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            return
        if name.startswith("sta"):
            m = await safe_reply_text(message, "🔎 Fetching Your personal stats.!")
            stats = await get_userss(message.from_user.id)
            if not stats:
                await asyncio.sleep(1)
                return await m.edit(_["ustats_1"])
            def get_stats():
                results = {}
                for i in stats:
                    results[str(i)] = stats[i]["spot"]
                if not results:
                    return None
                list_arranged = dict(sorted(results.items(), key=lambda item: item[1], reverse=True))
                tota = 0
                limit = 0
                videoid = None
                msg = ""
                for vidid, count in list_arranged.items():
                    tota += count
                    if limit == 10:
                        continue
                    if limit == 0:
                        videoid = vidid
                    limit += 1
                    details = stats.get(vidid)
                    title = (details["title"][:35]).title()
                    if vidid == "telegram":
                        msg += f"🔗[Telegram Files and Audio]({config.SUPPORT_GROUP}) ** played {count} Times**\n\n"
                    else:
                        msg += f"🔗 [{title}](https://www.youtube.com/watch?v={vidid}) ** played {count} Times**\n\n"
                return videoid, _["ustats_2"].format(len(stats), tota, limit) + msg
            try:
                res = await loop.run_in_executor(None, get_stats)
            except Exception:
                return
            if not res:
                return await m.edit(_["ustats_1"])
            videoid, msg = res
            thumbnail = await Platform.youtube.thumbnail(videoid, True)
            await m.delete()
            await safe_reply_photo(message, photo=thumbnail, caption=msg)
            return
        if name.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)
            await asyncio.sleep(1)
            if await is_on_off(config.LOG):
                sender_id = message.from_user.id
                sender_name = message.from_user.first_name or "Unknown"
                await safe_send_message(config.LOGGER_ID, f"{sender_name} Has just started bot to check Sudolist\n\nUser Id: {sender_id}\nUser Name: {sender_name}")
            return
        if name.startswith("lyr"):
            query = name.replace("lyrics_", "", 1)
            lyrics = config.lyrical.get(query)
            if lyrics:
                await Platform.telegram.send_split_text(message, lyrics)
                return
            await safe_reply_text(message, "Failed to get lyrics ")
            return
        if name.startswith("del"):
            await del_plist_msg(client=client, message=message, _=_)
            await asyncio.sleep(1)
            return
        if name.startswith("inf"):
            m = await safe_reply_text(message, "🔎 Fetching info..")
            query = f"https://www.youtube.com/watch?v={name.replace('info_', '', 1)}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = f"""
🔍__**Video track information **__

❇️**Title:** {title}

⏳**Duration:** {duration} Mins
👀**Views:** `{views}`
⏰**Published times:** {published}
🎥**Channel Name:** {channel}
📎**Channel Link:** [Visit from here]({channellink})
🔗**Videp linl:** [Link]({link})
"""
            key = InlineKeyboardMarkup([[InlineKeyboardButton(text="🎥 Watch ", url=f"{link}"), InlineKeyboardButton(text="🔄 Close", callback_data="close")]])
            await m.delete()
            await safe_send_photo(message.chat.id, photo=thumbnail, caption=searched_text, parse_mode=ParseMode.MARKDOWN, reply_markup=key)
            await asyncio.sleep(1)
            if await is_on_off(config.LOG):
                sender_id = message.from_user.id
                sender_name = message.from_user.first_name or "Unknown"
                await safe_send_message(config.LOGGER_ID, f"{sender_name} Has just started bot to check Video information\n\nUser Id: {sender_id}\nUser Name: {sender_name}")
            return
    else:
        try:
            await app.resolve_peer(OWNER_ID[0])
            OWNER = OWNER_ID[0]
        except Exception:
            OWNER = None
        out = private_panel(_, app.username, OWNER)
        mk = sanitize_markup(InlineKeyboardMarkup(out) if out else None)
        if START_IMG_URL:
            try:
                if mk:
                    await safe_reply_photo(message, photo=START_IMG_URL, caption=_["start_1"].format(getattr(app, "mention", app.username)), reply_markup=mk)
                else:
                    await safe_reply_photo(message, photo=START_IMG_URL, caption=_["start_1"].format(getattr(app, "mention", app.username)))
            except Exception:
                if mk:
                    await safe_reply_text(message, text=_["start_1"].format(getattr(app, "mention", app.username)), reply_markup=mk)
                else:
                    await safe_reply_text(message, text=_["start_1"].format(getattr(app, "mention", app.username)))
        else:
            if mk:
                await safe_reply_text(message, text=_["start_1"].format(getattr(app, "mention", app.username)), reply_markup=mk)
            else:
                await safe_reply_text(message, text=_["start_1"].format(getattr(app, "mention", app.username)))
        if await is_on_off(config.LOG):
            sender_id = message.from_user.id
            sender_name = message.from_user.first_name or "Unknown"
            await safe_send_message(config.LOGGER_ID, f"{sender_name} Has started bot.\n\nUser id: {sender_id}\nUser name: {sender_name}")


@app.on_message(command("START_COMMAND") & filters.group & ~BANNED_USERS)
@LanguageStart
async def testbot(client, message: Message, _):
    uptime = int(time.time() - _boot_)
    chat_id = message.chat.id
    await safe_reply_text(message, _["start_7"].format(get_readable_time(uptime)))
    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    chat_id = message.chat.id
    if config.PRIVATE_BOT_MODE == str(True):
        if not await is_served_private_chat(message.chat.id):
            await safe_reply_text(message, "**ᴛʜɪs ʙᴏᴛ's ᴘʀɪᴠᴀᴛᴇ ᴍᴏᴅᴇ ʜᴀs ʙᴇᴇɴ ᴇɴᴀʙʟᴇᴅ ᴏɴʟʏ ᴍʏ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ɪғ ᴡᴀɴᴛ ᴛᴏ ᴜsᴇ ᴛʜɪs ɪɴ ʏᴏᴜʀ ᴄʜᴀᴛ sᴏ sᴀʏ ᴛᴏ ᴍʏ ᴏᴡɴᴇʀ ᴛᴏ ᴀᴜᴛʜᴏʀɪᴢᴇ ʏᴏᴜʀ ᴄʜᴀᴛ.")
            return await app.leave_chat(message.chat.id)
    else:
        await add_served_chat(chat_id)
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if member.id == app.id:
                chat_type = message.chat.type
                if chat_type != ChatType.SUPERGROUP:
                    await safe_reply_text(message, _["start_5"])
                    return await app.leave_chat(message.chat.id)
                if chat_id in await blacklisted_chats():
                    await safe_reply_text(message, _["start_6"].format(f"https://t.me/{getattr(app, 'username', '')}?start=sudolist"))
                    return await app.leave_chat(chat_id)
                userbot = await get_assistant(message.chat.id)
                out = start_pannel(_)
                mk = sanitize_markup(InlineKeyboardMarkup(out) if out else None)
                await safe_reply_text(message, _["start_2"].format(getattr(app, "mention", getattr(app, "username", "")), getattr(userbot, "username", str(getattr(userbot, "id", ""))), getattr(userbot, "id", "")), reply_markup=mk)
            if member.id in OWNER_ID:
                await safe_reply_text(message, _["start_3"].format(getattr(app, "mention", getattr(app, "username", "")), getattr(member, "mention", member.first_name or "User")))
                return
            if member.id in SUDOERS:
                await safe_reply_text(message, _["start_4"].format(getattr(app, "mention", getattr(app, "username", "")), getattr(member, "mention", member.first_name or "User")))
                return
        except:
            returned 
