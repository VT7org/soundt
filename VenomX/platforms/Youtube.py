import asyncio
import os
import random
import re
import logging

from async_lru import alru_cache
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from yt_dlp import YoutubeDL

import aiohttp
import aiofiles
from config import API_URL
from VenomX.utils.database import is_on_off
from VenomX.utils.decorators import asyncify
from VenomX.utils.formatters import seconds_to_min, time_to_seconds

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

logger = logging.getLogger("YouTubeAPI")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

NOTHING = {"cookies_dead": None}

YTDOWNLOADER = True
YT_CONCURRENT_FRAGMENT_DOWNLOADS = 42

API_TIMEOUT = 120
USE_CHUNK_STREAM = True
CHUNK_SIZE_MB = 8
CHUNK_SIZE = CHUNK_SIZE_MB * 1024 * 1024

def cookies():
    folder_path = f"{os.getcwd()}/cookies"
    txt_files = [file for file in os.listdir(folder_path) if file.endswith(".txt")]
    if not txt_files:
        raise FileNotFoundError("No Cookies found in cookies directory make sure your cookies file written  .txt file")
    cookie_txt_file = random.choice(txt_files)
    cookie_txt_file = os.path.join(folder_path, cookie_txt_file)
    return cookie_txt_file

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    @property
    def use_fallback(self):
        return NOTHING["cookies_dead"] is True

    @use_fallback.setter
    def use_fallback(self, value):
        if NOTHING["cookies_dead"] is None:
            NOTHING["cookies_dead"] = value

    @asyncify
    def url(self, message_1: Message) -> str | None:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    @alru_cache(maxsize=None)
    async def details(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    @alru_cache(maxsize=None)
    async def title(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    @alru_cache(maxsize=None)
    async def duration(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    @alru_cache(maxsize=None)
    async def thumbnail(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        cmd = [
            "yt-dlp",
            f"--cookies",
            cookies(),
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    @alru_cache(maxsize=None)
    async def playlist(self, link, limit, videoid: bool | str = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        cmd = (
            f"yt-dlp -i --compat-options no-youtube-unavailable-videos "
            f'--get-id --flat-playlist --playlist-end {limit} --skip-download "{link}" '
            f"2>/dev/null"
        )
        playlist = await shell_cmd(cmd)
        try:
            result = [key for key in playlist.split("\n") if key]
        except Exception:
            result = []
        return result

    @alru_cache(maxsize=None)
    async def track(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if link.startswith("http://") or link.startswith("https://"):
            return await self._track(link)
        try:
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration_min = result["duration"]
                vidid = result["id"]
                yturl = result["link"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            track_details = {
                "title": title,
                "link": yturl,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }
            return track_details, vidid
        except Exception:
            return await self._track(link)

    @asyncify
    def _track(self, q):
        options = {
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": "in_playlist",
            "cookiefile": f"{cookies()}",
        }
        with YoutubeDL(options) as ydl:
            info_dict = ydl.extract_info(f"ytsearch: {q}", download=False)
            details = info_dict.get("entries")[0]
            info = {
                "title": details["title"],
                "link": details["url"],
                "vidid": details["id"],
                "duration_min": (
                    seconds_to_min(details["duration"])
                    if details["duration"] != 0
                    else None
                ),
                "thumb": details["thumbnails"][0]["url"],
            }
            return info, details["id"]

    @alru_cache(maxsize=None)
    @asyncify
    def formats(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {
            "quiet": True,
            "cookiefile": f"{cookies()}",
        }
        ydl = YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except Exception:
                    continue
                if "dash" not in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except KeyError:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    @alru_cache(maxsize=None)
    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: bool | str = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
        link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def _api_download(self, link: str, vidid: str, is_audio: bool) -> str | None:
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=100, force_close=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            for attempt in range(1, 5):
                try:
                    if is_audio:
                        params = {"id": vidid, "format": "mp3"}
                    else:
                        params = {"url": link, "format": "mp4"}
                    logger.info("API request -> attempt %s url=%s params=%s", attempt, API_URL, params)
                    async with session.get(API_URL, params=params) as resp:
                        logger.info("API response status: %s", resp.status)
                        if resp.status != 200:
                            raise Exception(f"Non-200 response: {resp.status}")
                        j = await resp.json()
                        data = j.get("data") or {}
                        dl_url = data.get("url")
                        file_format = data.get("format")
                        file_title = data.get("title") or vidid or "download"
                        if not dl_url:
                            raise Exception("Missing data.url")
                        ext = file_format or ("mp4" if not is_audio else "mp3")
                        filename = f"{vidid}.{ext}"
                        filepath = os.path.join(DOWNLOADS_DIR, filename)
                        logger.info("Starting full download from API -> %s", dl_url)
                        async with session.get(dl_url) as file_resp:
                            if file_resp.status != 200:
                                raise Exception(f"Download URL non-200: {file_resp.status}")
                            async with aiofiles.open(filepath, "wb") as afp:
                                if USE_CHUNK_STREAM:
                                    async for chunk in file_resp.content.iter_chunked(CHUNK_SIZE):
                                        await afp.write(chunk)
                                else:
                                    content = await file_resp.read()
                                    await afp.write(content)
                            logger.info("API download finished -> %s", filepath)
                            return filepath
                except asyncio.TimeoutError:
                    if attempt == 4:
                        logger.exception("API timed out after 4 attempts")
                        return None
                    wait = 2 * attempt
                    logger.warning("API timeout on attempt %s, retrying in %s seconds...", attempt, wait)
                    await asyncio.sleep(wait)
                except Exception as e:
                    logger.exception("API error on attempt %s: %s", attempt, e)
                    if attempt == 4:
                        logger.warning("API failed after 4 attempts, falling back to yt-dlp")
                        return None
                    wait = 2 * attempt
                    await asyncio.sleep(wait)
        return None

    async def download(
        self,
        link: str,
        mystic,
        video: bool | str = None,
        videoid: bool | str = None,
        songaudio: bool | str = None,
        songvideo: bool | str = None,
        format_id: bool | str = None,
        title: bool | str = None,
    ) -> str:
        if videoid:
            link = self.base + link

        def _extract_vid_id(url: str):
            m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
            if m:
                return m.group(1)
            return None

        vidid = _extract_vid_id(link)

        if API_URL and vidid:
            is_audio = songaudio or (not video and not songvideo and not songaudio)
            api_path = await self._api_download(link, vidid, is_audio)
            if api_path:
                return api_path, True

        @asyncify
        def audio_dl():
            import os
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "cookiefile": f"{cookies()}",
                "prefer_ffmpeg": True,
                "concurrent_fragment_downloads": YT_CONCURRENT_FRAGMENT_DOWNLOADS,
                "continuedl": True,
            }
            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link, False)
                xyz = os.path.join(DOWNLOADS_DIR, f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

        @asyncify
        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "cookiefile": f"{cookies()}",
                "concurrent_fragment_downloads": YT_CONCURRENT_FRAGMENT_DOWNLOADS,
                "continuedl": True,
            }
            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link, False)
                xyz = os.path.join(DOWNLOADS_DIR, f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

        @asyncify
        def song_video_dl():
            formats = f"{format_id}+140"
            ydl_optssx = {
                "format": formats,
                "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s_%(format_id)s.%(ext)s"),
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
                "cookiefile": f"{cookies()}",
                "concurrent_fragment_downloads": YT_CONCURRENT_FRAGMENT_DOWNLOADS,
                "continuedl": True,
            }
            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link)
                filename = f"{info['id']}_{format_id}.mp4"
                file_path = os.path.join(DOWNLOADS_DIR, filename)
                return file_path

        @asyncify
        def song_audio_dl():
            ydl_optssx = {
                "format": format_id,
                "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s_%(format_id)s.%(ext)s"),
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "cookiefile": f"{cookies()}",
                "concurrent_fragment_downloads": YT_CONCURRENT_FRAGMENT_DOWNLOADS,
                "continuedl": True,
            }
            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link)
                filename = f"{info['id']}_{format_id}.mp3"
                file_path = os.path.join(DOWNLOADS_DIR, filename)
                return file_path

        if songvideo:
            return await song_video_dl()
        elif songaudio:
            return await song_audio_dl()
        elif video:
            if await is_on_off(__import__("config").YTDOWNLOADER if hasattr(__import__("config"), "YTDOWNLOADER") else YTDOWNLOADER):
                direct = True
                downloaded_file = await video_dl()
            else:
                command = [
                    "yt-dlp",
                    f"--cookies",
                    cookies(),
                    "-g",
                    "-f",
                    "best",
                    link,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    downloaded_file = await video_dl()
                    direct = True
        else:
            direct = True
            downloaded_file = await audio_dl()
        return downloaded_file, direct
