import json
import random
import requests

from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from sightengine.client import SightengineClient

print("🔥 NSFW MODULE LOADED")

# ---------------- DATABASE ----------------
NSFW = MongoCli("mongodb+srv://nsfwstorage:a@cluster0.c3iqn53.mongodb.net/?appName=Cluster0")

stats_db = NSFW.Anonymous
nsfw_db = stats_db.nsfw_check.status

nsfw_cache = []
LOAD = False

# ---------------- API ----------------
api_credentials = [
    {'api_user': '1820340144', 'api_secret': 'sKYJTbM7EMA5ycYd8EKgLZF5BxEjmwwz'},
]

# ---------------- CACHE ----------------
async def load_caches():
    global nsfw_cache, LOAD

    if LOAD:
        return

    LOAD = True
    nsfw_cache = await nsfw_db.find().to_list(None)
    print("✅ NSFW cache loaded")
    LOAD = False


# ---------------- STATUS ----------------
async def get_nsfw_status(chat_id, bot_id):
    for data in nsfw_cache:
        if data.get("chat_id") == chat_id and data.get("bot_id") == bot_id:
            return data.get("status", "enabled")
    return "enabled"


# ---------------- ACTION ----------------
async def take_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    print("🚨 TAKING ACTION")

    try:
        await msg.delete()
    except Exception as e:
        print("Delete failed:", e)

    try:
        await context.bot.restrict_chat_member(
            msg.chat.id,
            msg.from_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        print("Restrict failed:", e)

    # 🔥 OPTIONAL BUTTON
    buttons = [
        [
            InlineKeyboardButton("🚫 Delete", callback_data="nsfw_delete"),
            InlineKeyboardButton("✅ Ignore", callback_data="nsfw_ignore")
        ]
    ]

    await context.bot.send_message(
        chat_id=msg.chat.id,
        text="⚠️ NSFW Detected",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ---------------- CALLBACK ----------------
async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    data = query.data

    if data == "nsfw_delete":
        await query.edit_message_text("🚫 Deleted by admin")

    elif data == "nsfw_ignore":
        await query.edit_message_text("✅ Ignored")

    else:
        await query.edit_message_text("⚠️ Unknown action")


# ---------------- NSFW COMMAND ----------------
async def nsfw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("⚙️ NSFW COMMAND TRIGGERED")

    if not context.args:
        return await update.message.reply_text("Use:\n/nsfwcheck on\n/nsfwcheck off")

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


# ---------------- NSFW CHECK ----------------
async def check_nsfw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔥 NSFW FUNCTION CALLED")

    msg = update.message
    if not msg:
        return

    if not (msg.photo or msg.sticker or msg.video or msg.animation):
        print("❌ NOT MEDIA")
        return

    chat_id = msg.chat.id
    bot_id = context.bot.id

    status = await get_nsfw_status(chat_id, bot_id)
    print("STATUS:", status)

    if status == "disabled":
        return

    try:
        creds = random.choice(api_credentials)

        # ---------------- PHOTO ----------------
        if msg.photo:
            file = await msg.photo[-1].get_file()
            url = file.file_path

            r = requests.get(
                "https://api.sightengine.com/1.0/check.json",
                params={
                    "url": url,
                    "models": "nudity-2.1",
                    "api_user": creds['api_user'],
                    "api_secret": creds['api_secret']
                }
            )

            data = r.json()
            score = max(data.get("nudity", {}).values(), default=0)

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

            for frame in output.get("data", {}).get("frames", []):
                score = max(frame.get("nudity", {}).values(), default=0)
                if score > 0.2:
                    return await take_action(update, context)

        # ---------------- STICKER ----------------
        elif msg.sticker:
            file = await context.bot.get_file(msg.sticker.file_id)
            url = file.file_path

            if msg.sticker.is_video or msg.sticker.is_animated:
                client = SightengineClient(creds['api_user'], creds['api_secret'])
                output = client.check('nudity-2.1').video_sync(url)

                for frame in output.get("data", {}).get("frames", []):
                    score = max(frame.get("nudity", {}).values(), default=0)
                    if score > 0.2:
                        return await take_action(update, context)

            else:
                r = requests.get(
                    "https://api.sightengine.com/1.0/check.json",
                    params={
                        "url": url,
                        "models": "nudity-2.1",
                        "api_user": creds['api_user'],
                        "api_secret": creds['api_secret']
                    }
                )

                data = r.json()
                score = max(data.get("nudity", {}).values(), default=0)

                if score > 0.25:
                    return await take_action(update, context)

    except Exception as e:
        print("❌ ERROR:", e)
