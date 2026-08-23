# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
#
# All rights reserved.

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ShrutiMusic import app
import os
import yt_dlp
import asyncio

@app.on_message(filters.command("vid"))
async def video_downloader(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide a video URL.\n\nExample:\n/vid Any_video_url")

    video_url = message.text.split(None, 1)[1]
    msg = await message.reply("🔍 Fetching and downloading video using yt-dlp...")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': ['player_client=android', 'player_skip=webpage']},
        'source_address': '0.0.0.0',
    }

    try:
        def download_video():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')

        # Run yt-dlp synchronously in an executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_video)

        await msg.edit("⬆️ Uploading video...")

        await app.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption=f"🎬 {title}\n\n✅",
            supports_streaming=True
        )

        await msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await msg.edit(f"❌ Error: {str(e)}")


REPO_VIDEO = "https://files.catbox.moe/aoafwn.mp4"

@app.on_message(filters.command(["repo", "source"]))
async def send_repo(_, message: Message):
    await message.reply_video(
        video=REPO_VIDEO,
        caption=(
            "<b>✨ ʜᴇʏ ᴅᴇᴀʀ, ʜᴇʀᴇ ɪꜱ ᴛʜᴇ ᴏꜰꜰɪᴄɪᴀʟ ʀᴇᴘᴏꜱɪᴛᴏʀʏ ᴏꜰ ᴛʜɪꜱ ʙᴏᴛ ✨</b>\n\n"
            "🔗 ᴏɴ'ᴛ ꜰᴏʀɢᴇᴛ ᴛᴏ ɢɪᴠᴇ ᴀ ꜱᴛᴀʀ 🌟 ᴀɴᴅ ꜰᴏʟʟᴏᴡ!\n\n"
            "🧡 ᴄʀᴇᴅɪᴛꜱ : <a href='https://t.me/ShrutiBots'>@ShrutiBots</a>"
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📂 Management Bot", url="http://github.com/NoxxOP/ShrutiMusic"),
                    InlineKeyboardButton("📂 Music Bot", url="http://github.com/NoxxOP/ShrutixMusic")
                ]
            ]
        ),
        supports_streaming=True,
    )
