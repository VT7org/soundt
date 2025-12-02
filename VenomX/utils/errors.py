import sys
import traceback
from functools import wraps
from datetime import datetime
from typing import Optional, Dict

from pyrogram.errors.exceptions.forbidden_403 import ChatWriteForbidden
try:
    from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid
except Exception:
    try:
        from pyrogram import errors as _py_errors
        PeerIdInvalid = getattr(_py_errors, "PeerIdInvalid", _py_errors.BadRequest)
    except Exception:
        PeerIdInvalid = Exception

from VenomX import app
from config import LOGGER_ID as LOG_ERROR_ID
from VenomX.utils.exceptions import is_ignored_error
from VenomX.utils.pastebin import TuneBin

MAX = 4096
DEBUG_IGNORE_LOG = True

def _chunk(text: str):
    if len(text) <= MAX:
        yield text
    else:
        lines = text.splitlines(keepends=True)
        buf = ""
        for line in lines:
            if len(buf) + len(line) > MAX:
                yield buf
                buf = line if len(line) <= MAX else ""
                if len(line) > MAX:
                    for i in range(0, len(line), MAX):
                        yield line[i:i+MAX]
            else:
                buf += line
        if buf:
            yield buf


async def send_log(text: str):
    if LOG_ERROR_ID:
        try:
            await app.send_message(LOG_ERROR_ID, text, disable_web_page_preview=True)
            return
        except (PeerIdInvalid, ChatWriteForbidden):
            pass
        except Exception:
            pass
    print(text)


async def send_large_error(text: str, caption: Optional[str] = None):
    paste = None
    try:
        paste = await TuneBin(text)
    except Exception:
        paste = None

    if paste:
        msg = (caption + "\n\n" if caption else "") + f"🔗 {paste}"
        await send_log(msg)
        return

    header = (caption + "\n\n") if caption else ""
    for chunk in _chunk(header + text):
        await send_log(chunk)


def format_trace(err, tb, label, extras: Optional[Dict] = None):
    exc = type(err).__name__
    parts = [
        f"🚨 <b>{label}</b>",
        f"📍 <b>Type:</b> <code>{exc}</code>"
    ]
    if extras:
        parts.extend([f"📌 <b>{k}:</b> <code>{v}</code>" for k, v in extras.items()])
    parts.append(f"\n<b>Traceback:</b>\n<pre>{tb}</pre>")
    return "\n".join(parts)


async def handle_trace(err, tb, label, extras=None):
    if is_ignored_error(err):
        await log_ignored(err, tb, label, extras)
        return

    try:
        formatted = format_trace(err, tb, label, extras)
        if len(formatted) > MAX:
            await send_large(tb, f"{label} (large traceback)")
        else:
            await send_log(formatted)
    except Exception as e:
        print("CRITICAL:", e, " | Original:", err)
        print(tb)


async def log_ignored(err, tb, label, extras=None):
    if not DEBUG_IGNORE_LOG:
        return

    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        f"--- Ignored | {label} @ {t} ---",
        f"Type: {type(err).__name__}"
    ]
    if extras:
        for k, v in extras.items():
            parts.append(f"{k}: {v}")
    parts += ["Traceback:", tb.strip(), "---------------------------"]

    payload = "\n".join(parts)
    if len(payload) > MAX:
        await send_large(payload, "Ignored Error")
    else:
        await send_log(payload)


async def log_internal(err, tb, extras=None):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        "=" * 60,
        f"Internal @ {t}",
        f"Type: {type(err).__name__}",
        f"Message: {str(err)}"
    ]
    if extras:
        for k, v in extras.items():
            parts.append(f"{k}: {v}")
    parts += ["Traceback:", tb.strip(), "=" * 60]

    payload = "\n".join(parts)
    if len(payload) > MAX:
        await send_large(payload, "Internal Error")
    else:
        await send_log(payload)


def capture_err(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except ChatWriteForbidden:
            try:
                await app.leave_chat(message.chat.id)
            except Exception:
                pass
        except Exception as err:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            extras = {
                "User": message.from_user.mention if getattr(message, "from_user", None) else "N/A",
                "Command": getattr(message, "text", None) or getattr(message, "caption", None) or "N/A",
                "Chat ID": getattr(message.chat, "id", "N/A")
            }
            await handle_trace(err, tb, "Error", extras)
    return wrapper


def capture_callback_err(func):
    @wraps(func)
    async def wrapper(client, cq, *args, **kwargs):
        try:
            return await func(client, cq, *args, **kwargs)
        except Exception as err:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            extras = {
                "User": cq.from_user.mention if getattr(cq, "from_user", None) else "N/A",
                "Chat ID": cq.message.chat.id if getattr(cq, "message", None) else "N/A"
            }
            await handle_trace(err, tb, "Callback Error", extras)
    return wrapper


def capture_internal_err(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as err:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            extras = {
                "Function": func.__name__,
                "Module": func.__module__
            }
            await log_internal(err, tb, extras)
    return wrapper
