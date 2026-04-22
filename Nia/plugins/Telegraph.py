import os
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import requests
import subprocess
import tempfile


def upload_file(file_path):
    if not os.path.isfile(file_path):
        return False, f"❖ ᴇʀʀᴏʀ : File not found at path {file_path}"

    try:
        with open(file_path, "rb") as f:
            url = "https://catbox.moe/user/api.php"
            data = {"reqtype": "fileupload", "json": "true"}
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            try:
                json_data = response.json()
                return True, json_data.get("url", "❖ Uploaded but URL not found")
            except Exception:
                return True, response.text.strip()  # fallback to raw text if not JSON
        else:
            return False, f"❖ ᴇʀʀᴏʀ : {response.status_code} - {response.text}"

    except Exception as e:
        return False, f"❖ ᴇxᴄᴇᴘᴛɪᴏɴ : {str(e)}"

@Client.on_message(filters.command(["tgm", "tgt", "telegraph", "tl"]))
async def get_link_group(client, message):
    if not message.reply_to_message:
        return await message.reply_text(
            "❖ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴏɴ ᴛᴇʟᴇɢʀᴀᴘʜ"
        )

    media = message.reply_to_message
    file_size = 0
    if media.photo:
        file_size = media.photo.file_size
    elif media.video:
        file_size = media.video.file_size
    elif media.document:
        file_size = media.document.file_size

    if file_size > 200 * 1024 * 1024:
        return await message.reply_text("ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴍᴇᴅɪᴀ ғɪʟᴇ ᴜɴᴅᴇʀ 200 MB")

    try:
        text = await message.reply("❍ ᴘʀᴏᴄᴇssɪɴɢ...")

        async def progress(current, total):
            try:
                await text.edit_text(f"❍ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ... {current * 100 / total:.1f}%")
            except Exception:
                pass

        try:
            local_path = await media.download(progress=progress)
            await text.edit_text("❍ ᴜᴘʟᴏᴀᴅɪɴɢ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴘʜ...")

            success, upload_path = upload_file(local_path)

            if success:
                await text.edit_text(
                    f"❖ | [ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ]({upload_path}) | ❖",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "• ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ •",
                                    url=upload_path,
                                )
                            ]
                        ]
                    ),
                )
            else:
                await text.edit_text(
                    f"❖ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴜᴘʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ғɪʟᴇ\n{upload_path}"
                )

            try:
                os.remove(local_path)
            except Exception:
                pass

        except Exception as e:
            await text.edit_text(f"❖ | ғɪʟᴇ ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ\n\n<i>❍ ʀᴇᴀsᴏɴ : {e}</i>")
            try:
                os.remove(local_path)
            except Exception:
                pass
            return
    except Exception:
        pass

import os
import tempfile
import subprocess

async def get_url(client, message):
    file_size = 0
    if message.photo:
        file_size = message.photo.file_size
    elif message.video:
        file_size = message.video.file_size
    elif message.animation:
        file_size = message.animation.file_size
    elif message.sticker:
        file_size = message.sticker.file_size
    elif message.document:
        file_size = message.document.file_size

    if file_size > 200 * 1024 * 1024:
        return

    try:
        local_path = await message.download()

        if message.sticker:
            if local_path.endswith('.webm'):
                local_path = await convert_sticker_to_image(client, message)
                success, upload_path = upload_file(local_path)
                if success:
                    return upload_path

        success, upload_path = upload_file(local_path)
        if success:
            print(upload_path)
            return upload_path

        try:
            os.remove(local_path)
        except Exception:
            pass

    except Exception as e:
        try:
            os.remove(local_path)
        except Exception:
            pass
        return


async def convert_sticker_to_image(client, message):
    try:
        sticker = await message.download(file_name=tempfile.gettempdir() + "/sticker.webm")
        output_path = tempfile.gettempdir() + "/sticker.jpg"
        ffmpeg_command = [
            "ffmpeg",
            "-i", sticker,
            "-vf", r"select=eq(n\,0)",
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(e)
        if os.path.exists(sticker):
            os.remove(sticker)
        if os.path.exists(output_path):
            os.remove(output_path)
        return None


async def convert_sticker_to_video(client, message):
    try:
        sticker = await message.download(file_name=tempfile.gettempdir() + "/sticker.webm")
        output_path = tempfile.gettempdir() + "/sticker.mp4"
        ffmpeg_command = [
            "ffmpeg",
            "-i", sticker,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:v", "800k",
            "-b:a", "128k",
            "-y",
            output_path
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_path):
            print(f"output path is: {output_path}")
            await message.reply_video(output_path)
            return output_path
    except Exception as e:
        print(e)
        if os.path.exists(sticker):
            os.remove(sticker)
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
