import os
import requests
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


# ---------------- UPLOAD ---------------- #

def upload_file(file_path):
    if not os.path.isfile(file_path):
        return False, "❖ Error: File not found"

    try:
        with open(file_path, "rb") as f:
            url = "https://catbox.moe/user/api.php"
            data = {"reqtype": "fileupload", "json": "true"}
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            try:
                return True, response.json().get("url")
            except:
                return True, response.text.strip()
        else:
            return False, f"{response.status_code} - {response.text}"

    except Exception as e:
        return False, str(e)


# ---------------- COMMAND ---------------- #

async def telegraph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.reply_to_message:
        return await message.reply_text("❖ Reply to a media file")

    media = message.reply_to_message
    file = None
    file_size = 0

    # 🔥 detect media type
    if media.photo:
        file = await context.bot.get_file(media.photo.file_id)
        file_size = media.photo.file_size

    elif media.video:
        file = await context.bot.get_file(media.video.file_id)
        file_size = media.video.file_size

    elif media.document:
        file = await context.bot.get_file(media.document.file_id)
        file_size = media.document.file_size

    elif media.animation:
        file = await context.bot.get_file(media.animation.file_id)
        file_size = media.animation.file_size

    elif media.sticker:
        file = await context.bot.get_file(media.sticker.file_id)
        file_size = media.sticker.file_size

    if not file:
        return await message.reply_text("❖ Unsupported media")

    # 🔥 size check (200MB)
    if file_size and file_size > 200 * 1024 * 1024:
        return await message.reply_text("❖ File must be under 200MB")

    text = await message.reply_text("⬇️ Downloading...")

    try:
        local_path = os.path.join(tempfile.gettempdir(), file.file_id)

        # download
        await file.download_to_drive(local_path)

        await text.edit_text("⬆️ Uploading to Telegraph...")

        success, link = upload_file(local_path)

        if success:
            await text.edit_text(
                f"✅ Telegraph Link:\n{link}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Open Link", url=link)]]
                ),
            )
        else:
            await text.edit_text(f"❌ Upload failed:\n{link}")

        # cleanup
        try:
            os.remove(local_path)
        except:
            pass

    except Exception as e:
        await text.edit_text(f"❌ Error:\n{e}")


# ---------------- GET URL (FOR NSFW ETC) ---------------- #

async def get_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.callback_query.message

    if not message:
        return None

    file = None
    file_size = 0

    if message.photo:
        file = await context.bot.get_file(message.photo[-1].file_id)
        file_size = message.photo[-1].file_size

    elif message.video:
        file = await context.bot.get_file(message.video.file_id)
        file_size = message.video.file_size

    elif message.document:
        file = await context.bot.get_file(message.document.file_id)
        file_size = message.document.file_size

    elif message.animation:
        file = await context.bot.get_file(message.animation.file_id)
        file_size = message.animation.file_size

    elif message.sticker:
        file = await context.bot.get_file(message.sticker.file_id)
        file_size = message.sticker.file_size

    if not file:
        return None

    if file_size and file_size > 200 * 1024 * 1024:
        return None

    try:
        local_path = os.path.join(tempfile.gettempdir(), file.file_id)

        await file.download_to_drive(local_path)

        success, url = upload_file(local_path)

        try:
            os.remove(local_path)
        except:
            pass

        if success:
            return url

    except Exception as e:
        print(f"[get_url error] {e}")

    return None
