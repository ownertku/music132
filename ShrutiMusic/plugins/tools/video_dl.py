# =============================================
# ShrutiMusic - Video Downloader Plugin
# =============================================
# Commands:
#   /dl   <url>              - Auto detect & download (MP3 or MP4)
#   /song <url or query>     - Download MP3 (320kbps)
#   /ytdl <url>              - Download MP4 video (highest quality)
#   /dlq  <url> <quality>    - Download MP4 at specific quality (360/480/720/1080)
#
# Author: @NoxxOP | ShrutiBots
# =============================================

import os
import asyncio
import aiohttp
import aiofiles
import tempfile
from pathlib import Path

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from ShrutiMusic import app

BOT_USERNAME = os.environ.get("BOT_USERNAME", "ShrutiMusicBot")

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────


DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_TG_AUDIO_SIZE  = 50 * 1024 * 1024   # 50 MB Telegram limit for bots
MAX_TG_VIDEO_SIZE  = 2000 * 1024 * 1024 # 2 GB


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def format_duration(secs) -> str:
    if not secs:
        return "Unknown"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


async def fetch_info(url: str) -> dict | None:
    """Fetch video metadata using yt-dlp."""
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }
        
        def _extract():
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
                
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(None, _extract)
        
        if not info_dict:
            return None
            
        return {
            "title": info_dict.get("title", "Unknown"),
            "uploader": info_dict.get("uploader", "Unknown"),
            "duration_seconds": info_dict.get("duration"),
            "platform": info_dict.get("extractor", "Unknown"),
            "thumbnail": info_dict.get("thumbnail")
        }
    except Exception as e:
        print(f"fetch_info error: {e}")
        return None


async def download_from_api(
    url: str,
    dl_type: str,
    quality: str,
    out_path: str,
) -> bool:
    """Stream download from yt-dlp and save to out_path. Returns True on success."""
    try:
        if dl_type == "audio":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_path,
                "quiet": True,
                "no_warnings": True,
            }
        else:
            if quality == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            
            ydl_opts = {
                "format": fmt,
                "outtmpl": out_path,
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
            }

        def _download():
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _download)
        
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as e:
        print(f"download_from_api error: {e}")
        return False


def make_quality_keyboard(url: str) -> InlineKeyboardMarkup:
    """Inline keyboard for choosing video quality."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 MP3 320kbps", callback_data=f"dl|audio|best|{url}"),
        ],
        [
            InlineKeyboardButton("📹 360p",  callback_data=f"dl|video|360|{url}"),
            InlineKeyboardButton("📹 480p",  callback_data=f"dl|video|480|{url}"),
        ],
        [
            InlineKeyboardButton("🎬 720p HD",  callback_data=f"dl|video|720|{url}"),
            InlineKeyboardButton("🎬 1080p FHD", callback_data=f"dl|video|1080|{url}"),
        ],
        [
            InlineKeyboardButton("✨ Best Quality", callback_data=f"dl|video|best|{url}"),
        ],
    ])


# ─────────────────────────────────────────────────────────────
# /dl command – shows info + quality picker
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command(["dl", "download"]))
async def dl_command(_, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/dl <URL>` — Pick quality interactively\n"
            "`/song <URL or song name>` — Download MP3\n"
            "`/ytdl <URL>` — Download best MP4\n"
            "`/dlq <URL> <360|480|720|1080>` — Specific quality\n\n"
            "**Supported:** YouTube, Instagram, TikTok, Twitter, Facebook, SoundCloud & more"
        )

    url = args[1].strip()
    if not is_url(url):
        return await message.reply_text("❌ Please provide a valid URL starting with http:// or https://")

    status_msg = await message.reply_text("🔍 **Fetching video info…**")

    info = await fetch_info(url)
    if not info:
        return await status_msg.edit_text(
            "❌ **Failed to fetch info.**\n"
            "Make sure the URL is correct and the platform is supported."
        )

    title    = info.get("title", "Unknown")
    uploader = info.get("uploader", "Unknown")
    duration = format_duration(info.get("duration_seconds"))
    platform = info.get("platform", "Unknown")
    thumb    = info.get("thumbnail")

    caption = (
        f"🎬 **{title}**\n\n"
        f"👤 **Channel:** {uploader}\n"
        f"⏱ **Duration:** {duration}\n"
        f"🌐 **Platform:** {platform}\n\n"
        f"**Choose download format & quality:**"
    )

    try:
        await status_msg.delete()
        if thumb:
            await message.reply_photo(
                photo=thumb,
                caption=caption,
                reply_markup=make_quality_keyboard(url),
            )
        else:
            await message.reply_text(caption, reply_markup=make_quality_keyboard(url))
    except Exception:
        await status_msg.edit_text(caption, reply_markup=make_quality_keyboard(url))


# ─────────────────────────────────────────────────────────────
# Callback handler for quality selection
# ─────────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^dl\|"))
async def dl_callback(_, query: CallbackQuery):
    try:
        _, dl_type, quality, url = query.data.split("|", 3)
    except ValueError:
        return await query.answer("❌ Invalid data", show_alert=True)

    await query.answer("⏳ Starting download…")
    chat_id = query.message.chat.id
    user = query.from_user

    # Edit to show progress
    try:
        await query.message.edit_caption(
            f"⬇️ **Downloading {'🎵 MP3' if dl_type == 'audio' else '🎬 MP4 ' + quality}…**\n\n"
            f"Please wait, this may take a moment."
        )
    except Exception:
        pass

    # Determine extension
    ext = "mp3" if dl_type == "audio" else "mp4"
    out_path = str(DOWNLOAD_DIR / f"dl_{user.id}_{query.id[:8]}.{ext}")

    success = await download_from_api(url, dl_type, quality, out_path)

    if not success:
        return await query.message.edit_caption(
            "❌ **Download failed.**\nThe video may be too large, geo-restricted, or unavailable."
        )

    file_size = os.path.getsize(out_path)
    size_str  = format_size(file_size)

    try:
        if dl_type == "audio":
            if file_size > MAX_TG_AUDIO_SIZE:
                await query.message.edit_caption(
                    f"❌ **File too large ({size_str}).**\nTelegram allows max 50 MB for audio."
                )
                return
            await query.message.edit_caption(f"⬆️ **Uploading MP3…** ({size_str})")
            await app.send_audio(
                chat_id=chat_id,
                audio=out_path,
                caption=f"🎵 Downloaded by @{BOT_USERNAME}",
                thumb=query.message.photo.file_id if query.message.photo else None,
            )
        else:
            if file_size > MAX_TG_VIDEO_SIZE:
                await query.message.edit_caption(
                    f"❌ **File too large ({size_str}).**\nTelegram allows max 2 GB for video."
                )
                return
            await query.message.edit_caption(f"⬆️ **Uploading MP4 ({quality})…** ({size_str})")
            await app.send_video(
                chat_id=chat_id,
                video=out_path,
                caption=f"🎬 Downloaded by @{BOT_USERNAME}",
                supports_streaming=True,
            )

        try:
            await query.message.delete()
        except Exception:
            pass

    except Exception as e:
        await query.message.edit_caption(f"❌ Upload failed: {str(e)[:200]}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


# ─────────────────────────────────────────────────────────────
# /song – Direct MP3 download
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command(["song", "mp3"]))
async def song_command(_, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/song <YouTube URL or song name>`\n\n"
            "Downloads MP3 at **320kbps** highest quality."
        )

    query = args[1].strip()

    # If not a URL, search on YouTube
    if not is_url(query):
        status_msg = await message.reply_text(f"🔍 Searching: **{query}**…")
        try:
            from youtubesearchpython import VideosSearch
            search = VideosSearch(query, limit=1)
            result = (await asyncio.get_event_loop().run_in_executor(None, search.getNextPage))
            if not result or not result.get("result"):
                return await status_msg.edit_text("❌ No results found for your search.")
            url = result["result"][0]["link"]
            title_found = result["result"][0]["title"]
            await status_msg.edit_text(f"✅ Found: **{title_found}**\n⬇️ Downloading MP3…")
        except Exception as e:
            return await status_msg.edit_text(f"❌ Search failed: {str(e)[:200]}")
    else:
        url = query
        status_msg = await message.reply_text("⬇️ **Downloading MP3 (320kbps)…**")

    out_path = str(DOWNLOAD_DIR / f"song_{message.from_user.id}_{message.id}.mp3")
    success = await download_from_api(url, "audio", "best", out_path)

    if not success:
        return await status_msg.edit_text("❌ Download failed. Please check the URL.")

    file_size = os.path.getsize(out_path)
    if file_size > MAX_TG_AUDIO_SIZE:
        os.remove(out_path)
        return await status_msg.edit_text(f"❌ File too large ({format_size(file_size)}). Max: 50 MB.")

    try:
        await status_msg.edit_text(f"⬆️ Uploading MP3… ({format_size(file_size)})")
        await app.send_audio(
            chat_id=message.chat.id,
            audio=out_path,
            caption=f"🎵 Requested by {message.from_user.mention}",
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {str(e)[:200]}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


# ─────────────────────────────────────────────────────────────
# /ytdl – Direct best-quality MP4 download
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command(["ytdl", "video", "mp4"]))
async def ytdl_command(_, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/ytdl <URL>`\n\n"
            "Downloads best available MP4 video.\n"
            "For specific quality use `/dlq <URL> <360|480|720|1080>`"
        )

    url = args[1].strip()
    if not is_url(url):
        return await message.reply_text("❌ Please provide a valid URL.")

    status_msg = await message.reply_text("⬇️ **Downloading best quality MP4…**")
    out_path = str(DOWNLOAD_DIR / f"ytdl_{message.from_user.id}_{message.id}.mp4")

    success = await download_from_api(url, "video", "best", out_path)
    if not success:
        return await status_msg.edit_text("❌ Download failed. Please check the URL.")

    file_size = os.path.getsize(out_path)
    if file_size > MAX_TG_VIDEO_SIZE:
        os.remove(out_path)
        return await status_msg.edit_text(f"❌ File too large ({format_size(file_size)}). Max: 2 GB.")

    try:
        await status_msg.edit_text(f"⬆️ Uploading MP4… ({format_size(file_size)})")
        await app.send_video(
            chat_id=message.chat.id,
            video=out_path,
            caption=f"🎬 Requested by {message.from_user.mention}",
            supports_streaming=True,
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {str(e)[:200]}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


# ─────────────────────────────────────────────────────────────
# /dlq – Specific quality download
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("dlq"))
async def dlq_command(_, message: Message):
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text(
            "❌ **Usage:** `/dlq <URL> <quality>`\n\n"
            "**Quality options:** `360` `480` `720` `1080`\n\n"
            "**Example:** `/dlq https://youtu.be/xxx 1080`"
        )

    url     = args[1].strip()
    quality = args[2].strip()

    if quality not in ("360", "480", "720", "1080"):
        return await message.reply_text("❌ Quality must be one of: `360` `480` `720` `1080`")

    if not is_url(url):
        return await message.reply_text("❌ Please provide a valid URL.")

    status_msg = await message.reply_text(f"⬇️ **Downloading {quality}p MP4…**")
    out_path = str(DOWNLOAD_DIR / f"dlq_{message.from_user.id}_{message.id}.mp4")

    success = await download_from_api(url, "video", quality, out_path)
    if not success:
        return await status_msg.edit_text("❌ Download failed.")

    file_size = os.path.getsize(out_path)
    try:
        await status_msg.edit_text(f"⬆️ Uploading {quality}p MP4… ({format_size(file_size)})")
        await app.send_video(
            chat_id=message.chat.id,
            video=out_path,
            caption=f"🎬 {quality}p • Requested by {message.from_user.mention}",
            supports_streaming=True,
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {str(e)[:200]}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
