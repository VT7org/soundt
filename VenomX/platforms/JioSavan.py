# All rights reserved.
#

import os
import asyncio

import aiohttp
import yt_dlp

from io import BytesIO
from PIL import Image

from config import seconds_to_time
from VenomX.utils.decorators import asyncify


class Saavn:

    @staticmethod
    async def valid(url: str) -> bool:
        return "jiosaavn.com" in url

    @staticmethod
    async def is_song(url: str) -> bool:
        return "song" in url and not "/featured/" in url and "/album/" not in url

    @staticmethod
    async def is_playlist(url: str) -> bool:
        return "/featured/" in url or "/album" in url

    def clean_url(self, url: str) -> str:
        if "#" in url:
            url = url.split("#")[0]
        return url

    @asyncify
    def playlist(self, url, limit):
        clean_url = self.clean_url(url)
        api_url = f"https://saavnapi-nine.vercel.app/result?query={clean_url}&lyrics=false"

        async def _fetch():
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    data = await resp.json()
                    results = []
                    if isinstance(data, list):
                        for entry in data[:limit]:
                            duration = int(entry.get("duration") or 0)
                            results.append({
                                "title": entry.get("song") or entry.get("name") or "",
                                "duration_sec": duration,
                                "duration_min": seconds_to_time(duration),
                                "thumb": entry.get("image", ""),
                                "url": entry.get("perma_url", ""),
                                "id": entry.get("id", ""),
                            })
                    elif isinstance(data, dict):
                        songs = []
                        if "songs" in data and isinstance(data["songs"], list):
                            songs = data["songs"]
                        elif "content_list" in data and "songs" in data:
                            songs = data.get("songs", [])
                        elif "content_list" in data and isinstance(data["content_list"], list):
                            # content_list contains ids; try to map from songs if present
                            songs = data.get("songs", [])
                            if not songs:
                                songs = []
                        for entry in songs[:limit]:
                            duration = int(entry.get("duration") or 0)
                            results.append({
                                "title": entry.get("song") or entry.get("name") or "",
                                "duration_sec": duration,
                                "duration_min": seconds_to_time(duration),
                                "thumb": entry.get("image", ""),
                                "url": entry.get("perma_url", ""),
                                "id": entry.get("id", ""),
                            })
                    return results

        return asyncio.run(_fetch())

    async def info(self, url):
        url = self.clean_url(url)
        async with aiohttp.ClientSession() as session:
            if "jiosaavn.com" in url and "song" in url:
                api_url = "https://saavnapi-nine.vercel.app/lyrics/"
                params = {"query": url, "lyrics": "false"}
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    info = data
                    duration = int(info.get("duration") or 0)
                    thumb_url = info.get("image", "")
                    thumb_path = await self._resize_thumb(thumb_url, info.get("id", ""))
                    return {
                        "title": info.get("song", info.get("name", "")),
                        "duration_sec": duration,
                        "duration_min": seconds_to_time(duration),
                        "thumb": thumb_path,
                        "url": self.clean_url(info.get("perma_url", info.get("url", url))),
                        "_download_url": info.get("media_url"),
                        "_id": info.get("id"),
                    }
            else:
                api_url = "https://saavnapi-nine.vercel.app/result"
                params = {"query": url, "lyrics": "false"}
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    if isinstance(data, list) and data:
                        info = data[0]
                    elif isinstance(data, dict):
                        if "songs" in data and isinstance(data["songs"], list) and data["songs"]:
                            info = data["songs"][0]
                        else:
                            # fallback to dict itself
                            info = data
                    else:
                        info = {}
                    duration = int(info.get("duration") or 0)
                    thumb_url = info.get("image", "")
                    thumb_path = await self._resize_thumb(thumb_url, info.get("id", ""))
                    return {
                        "title": info.get("song", info.get("name", "")),
                        "duration_sec": duration,
                        "duration_min": seconds_to_time(duration),
                        "thumb": thumb_path,
                        "url": self.clean_url(info.get("perma_url", info.get("url", url))),
                        "_download_url": info.get("media_url"),
                        "_id": info.get("id"),
                    }

    async def download(self, url):
        details = await self.info(url)
        file_path = os.path.join("downloads", f"Saavn_{details['_id']}.m4a")

        if not os.path.exists(file_path):
            async with aiohttp.ClientSession() as session:
                download_url = details.get("_download_url")
                if not download_url:
                    raise ValueError("No download URL found")
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        with open(file_path, "wb") as f:
                            while chunk := await resp.content.read(1024):
                                f.write(chunk)
                    else:
                        raise ValueError(
                            f"Failed to download {download_url}. HTTP Status: {resp.status}"
                        )

        details["filepath"] = file_path
        return file_path, details

    async def _resize_thumb(self, thumb_url, _id, size=(1280, 720)):
        thumb_path = os.path.join("cache", f"Thumb_{_id}.jpg")

        if os.path.exists(thumb_path):
            return thumb_path

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as response:
                img_data = await response.read()

        img = Image.open(BytesIO(img_data))
        scale_factor = size[1] / img.height
        new_width = int(img.width * scale_factor)
        new_height = size[1]

        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        new_img = Image.new("RGB", size, (0, 0, 0))
        new_img.paste(resized_img, ((size[0] - new_width) // 2, 0))

        new_img.save(thumb_path, format="JPEG")
        return thumb_path

    async def track(self, query, limit=10):
        q = query.strip()
        api_url = "https://saavnapi-nine.vercel.app/result"
        params = {"query": q, "lyrics": "false"}
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as resp:
                data = await resp.json()
                results = []
                if isinstance(data, list):
                    for entry in data[:limit]:
                        duration = int(entry.get("duration") or 0)
                        results.append({
                            "title": entry.get("song") or entry.get("name") or "",
                            "duration_sec": duration,
                            "duration_min": seconds_to_time(duration),
                            "thumb": entry.get("image", ""),
                            "url": entry.get("perma_url", entry.get("url", "")),
                            "_download_url": entry.get("media_url"),
                            "_id": entry.get("id"),
                        })
                elif isinstance(data, dict):
                    # albums, playlists or single dict
                    songs = []
                    if "songs" in data and isinstance(data["songs"], list):
                        songs = data["songs"]
                    elif "content_list" in data and isinstance(data.get("songs"), list):
                        songs = data.get("songs", [])
                    elif "songs" in data and isinstance(data["songs"], dict):
                        songs = [data["songs"]]
                    else:
                        # try to handle when dict is single song
                        if data.get("media_url") or data.get("id"):
                            songs = [data]
                    for entry in songs[:limit]:
                        duration = int(entry.get("duration") or 0)
                        results.append({
                            "title": entry.get("song") or entry.get("name") or "",
                            "duration_sec": duration,
                            "duration_min": seconds_to_time(duration),
                            "thumb": entry.get("image", ""),
                            "url": entry.get("perma_url", entry.get("url", "")),
                            "_download_url": entry.get("media_url"),
                            "_id": entry.get("id"),
                        })
                return results
