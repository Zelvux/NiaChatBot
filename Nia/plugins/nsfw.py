import json
import random
import asyncio
import requests
import os
import tempfile

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)

from telegram.ext import (
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters
)

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from sightengine.client import SightengineClient

# ---------------- DATABASE ----------------
NSFW = MongoCli("mongodb+srv://nsfwstorage:a@cluster0.c3iqn53.mongodb.net/?appName=Cluster0")

stats_db = NSFW.Anonymous
nsfw_storage = NSFW.STORAGE

nsfw_db = stats_db.nsfw_check.status
nsfw_block_db = nsfw_storage.nsfw_block.sticker
nsfw_ignore_db = nsfw_storage.nsfw_ignore.sticker

nsfw_cache = []
nsfw_block_cache = []
nsfw_ignore_cache = []

LOAD = False

# 🔥 MULTI API (SAFE)
api_credentials = [
    {'api_user': '1820340144', 'api_secret': 'sKYJTbM7EMA5ycYd8EKgLZF5BxEjmwwz'},
]

# ---------------- CACHE ----------------
async def load_caches():
    global nsfw_cache, nsfw_block_cache, nsfw_ignore_cache, LOAD

    if LOAD:
        return

    LOAD = True

    nsfw_cache = await nsfw_db.find().to_list(None)
    nsfw_block_cache = await nsfw_block_db.find().to_list(None)
    nsfw_ignore_cache = await nsfw_ignore_db.find().to_list(None)

    print("✅ NSFW cache loaded")
    LOAD = False


# ---------------- STATUS ----------------
async def get_nsfw_status(chat_id, bot_id):
    for data in nsfw_cache:
        if data.get("chat_id") == chat_id and data.get("bot_id") == bot_id:
            return data.get("status", "enabled")
    return "enabled"


# ---------------- ADMIN CHECK ----------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------- COMMAND ----------------
async def nsfw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Use:\n/nsfwcheck on\n/nsfwcheck off")

    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Admin only command")

    flag = context.args[0].lower()

    chat_id = update.effective_chat.id
    bot_id = context.bot.id

    if flag in ["on", "enable"]:
        await nsfw_db.update_one(
            {"chat_id": chat_id, "bot_id": bot_id},
            {"$set": {"status": "enabled"}},
            upsert=True
        )
        await update.message.reply_text("✅ NSFW Enabled")

    elif flag in ["off", "disable"]:
        await nsfw_db.update_one(
            {"chat_id": chat_id, "bot_id": bot_id},
            {"$set": {"status": "disabled"}},
            upsert=True
        )
        await update.message.reply_text("❌ NSFW Disabled")

    await load_caches()


# ---------------- ACTION ----------------
async def take_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    try:
        await msg.delete()
    except Exception as e:
        print("Delete failed:", e)

    try:
        user = msg.from_user.mention_html()
    except:
        user = "Unknown"

    text = f"🚫 NSFW Detected\n\nUser: {user}"

    await msg.chat.send_message(text, parse_mode="HTML")

    try:
        await context.bot.restrict_chat_member(
            msg.chat.id,
            msg.from_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        print("Restrict failed:", e)


# ---------------- REVIEW ----------------
async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Action Done")


# ---------------- NSFW CHECK ----------------
async def check_nsfw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg:
        return

    if not (msg.photo or msg.sticker or msg.animation or msg.video):
        return

    chat_id = msg.chat.id
    bot_id = context.bot.id

    status = await get_nsfw_status(chat_id, bot_id)

    if status == "disabled":
        return

    try:
        creds = random.choice(api_credentials)

        # ---------------- PHOTO ----------------
        if msg.photo:
            file = await msg.photo[-1].get_file()
            url = file.file_path

            params = {
                "url": url,
                "models": "nudity-2.1",
                "api_user": creds['api_user'],
                "api_secret": creds['api_secret']
            }

            r = requests.get("https://api.sightengine.com/1.0/check.json", params=params)
            data = json.loads(r.text)

            nudity = data.get("nudity", {})
            score = max(nudity.values()) if nudity else 0

            if score > 0.25:
                return await take_action(update, context)

        # ---------------- VIDEO / GIF ----------------
        elif msg.video or msg.animation:
            file = await context.bot.get_file(
                msg.video.file_id if msg.video else msg.animation.file_id
            )
            url = file.file_path

            client = SightengineClient(creds['api_user'], creds['api_secret'])
            output = client.check('nudity-2.1').video_sync(url)

            for frame in output.get('data', {}).get('frames', []):
                nudity = frame.get('nudity', {})

                if max(nudity.values(), default=0) > 0.2:
                    return await take_action(update, context)

        # ---------------- STICKER ----------------
        elif msg.sticker:
            file = await context.bot.get_file(msg.sticker.file_id)
            url = file.file_path

            # 🔥 VIDEO STICKER
            if msg.sticker.is_video or msg.sticker.is_animated:
                client = SightengineClient(creds['api_user'], creds['api_secret'])
                output = client.check('nudity-2.1').video_sync(url)

                for frame in output.get('data', {}).get('frames', []):
                    nudity = frame.get('nudity', {})

                    if max(nudity.values(), default=0) > 0.2:
                        return await take_action(update, context)

            # 🔥 NORMAL STICKER
            else:
                params = {
                    "url": url,
                    "models": "nudity-2.1",
                    "api_user": creds['api_user'],
                    "api_secret": creds['api_secret']
                }

                r = requests.get("https://api.sightengine.com/1.0/check.json", params=params)
                data = json.loads(r.text)

                nudity = data.get("nudity", {})
                score = max(nudity.values()) if nudity else 0

                if score > 0.25:
                    return await take_action(update, context)

    except Exception as e:
        print("NSFW Error:", e)
