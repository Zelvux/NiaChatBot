import asyncio
import random
import json
import shutil

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMembersFilter

from sightengine.client import SightengineClient
from Nia.utils import SUDO_USERS as SUDOERS
from Nia.plugins.Telegraph import get_url

import requests

# ---------------- DB ---------------- #

NSFW = MongoCli("mongodb+srv://nsfwstorage:a@cluster0.c3iqn53.mongodb.net/?appName=Cluster0")
stats_db = NSFW.Anonymous
nsfw_storage = NSFW.STORAGE

nsfw_db = stats_db.nsfw_check.status
nsfw_block_db = nsfw_storage.nsfw_block.sticker
nsfw_ignore_db = nsfw_storage.nsfw_ignore.sticker

nsfw_cache = []
LOAD = False

# ---------------- API KEYS ---------------- #

api_credentials = [
    {'api_user': '1226977330', 'api_secret': 'oKUPqWsQ8npZ6rHvmjmdj4gQZuhCzvWA'},
    {'api_user': '1820340144', 'api_secret': 'sKYJTbM7EMA5ycYd8EKgLZF5BxEjmwwz'},
]

# ---------------- CACHE ---------------- #

async def load_caches():
    global nsfw_cache, LOAD

    if LOAD:
        return

    LOAD = True
    nsfw_cache.clear()

    try:
        nsfw_cache = await nsfw_db.find().to_list(None)
    except Exception as e:
        print("Cache error:", e)

    LOAD = False


async def get_nsfw_status(chat_id, bot_id):
    for data in nsfw_cache:
        if data.get("chat_id") == chat_id and data.get("bot_id") == bot_id:
            return data.get("status", "enabled")
    return "enabled"

# ---------------- ADMIN ---------------- #

async def is_admin(client, chat_id, user_id):
    try:
        admins = [
            admin.user.id async for admin in client.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            )
        ]
        return user_id in admins or user_id in SUDOERS
    except:
        return user_id in SUDOERS

# ---------------- COMMAND ---------------- #

@Client.on_message(filters.command(["nsfwcheck"]), group=0)
async def nsfw_command(client: Client, message: Message):

    command = (message.text or "").split()

    if len(command) < 2:
        return await message.reply_text("Use: /nsfwcheck on/off")

    flag = command[1].lower()
    chat_id = message.chat.id
    bot_id = client.me.id

    if not await is_admin(client, chat_id, message.from_user.id):
        return await message.reply_text("Admin only ❌")

    if flag in ["on", "enable"]:
        await nsfw_db.update_one(
            {"chat_id": chat_id, "bot_id": bot_id},
            {"$set": {"status": "enabled"}},
            upsert=True
        )
        await message.reply_text("NSFW enabled ✅")
        await load_caches()

    elif flag in ["off", "disable"]:
        await nsfw_db.update_one(
            {"chat_id": chat_id, "bot_id": bot_id},
            {"$set": {"status": "disabled"}},
            upsert=True
        )
        await message.reply_text("NSFW disabled ❌")
        await load_caches()

# ---------------- ACTION ---------------- #

async def take_action(client, message):
    try:
        await message.delete()
        await message.reply_text("🚫 NSFW detected")
    except:
        pass

# ---------------- REVIEW ---------------- #

async def take_review(client, message, action):
    REVIEW_CHANNEL = -1003953222870
    try:
        if message.photo:
            await client.send_photo(REVIEW_CHANNEL, message.photo.file_id, caption=action)
        elif message.video:
            await client.send_video(REVIEW_CHANNEL, message.video.file_id, caption=action)
    except:
        pass

# ---------------- CHECK PHOTO ---------------- #

async def check_nsfw_photo(client, message):

    if await get_nsfw_status(message.chat.id, client.me.id) == "disabled":
        return

    url = await get_url(client, message)

    for creds in api_credentials:
        try:
            r = requests.get(
                "https://api.sightengine.com/1.0/check.json",
                params={
                    "url": url,
                    "models": "nudity-2.1",
                    "api_user": creds["api_user"],
                    "api_secret": creds["api_secret"],
                },
            )
            data = r.json()

            if data.get("nudity", {}).get("sexual_activity", 0) > 0.4:
                await take_review(client, message, "blocked")
                return await take_action(client, message)

            return
        except:
            continue

# ---------------- CHECK VIDEO ---------------- #

async def check_nsfw_video(client, message):

    if await get_nsfw_status(message.chat.id, client.me.id) == "disabled":
        return

    url = await get_url(client, message)

    for creds in api_credentials:
        try:
            se = SightengineClient(creds["api_user"], creds["api_secret"])
            result = se.check("nudity-2.1").video_sync(url)

            for frame in result.get("data", {}).get("frames", []):
                if frame.get("nudity", {}).get("sexual_activity", 0) > 0.1:
                    await take_review(client, message, "blocked")
                    return await take_action(client, message)
            return
        except:
            continue

# ---------------- BLOCK ---------------- #

@Client.on_message(filters.command(["blockpack"]) & filters.user(list(SUDOERS)), group=0)
async def block_pack_handler(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_unique_id
        await nsfw_block_db.insert_one({"file_id": file_id})
        await message.reply("Blocked ✅")

# ---------------- UNBLOCK ---------------- #

@Client.on_message(filters.command(["unblockpack"]) & filters.user(list(SUDOERS)), group=0)
async def unblock_pack_handler(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_unique_id
        await nsfw_ignore_db.insert_one({"file_id": file_id})
        await message.reply("Unblocked ✅")

# ---------------- MAIN ---------------- #

@Client.on_message(
    filters.incoming & ~filters.command(["nsfwcheck", "blockpack", "unblockpack"]),
    group=1
)
async def nsfws(client: Client, message: Message):

    if not nsfw_cache:
        await load_caches()

    if message.photo:
        asyncio.create_task(check_nsfw_photo(client, message))

    elif message.video:
        asyncio.create_task(check_nsfw_video(client, message))
