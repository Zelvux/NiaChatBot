import asyncio
import random
import json
import shutil

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli

from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    ChatPermissions
)
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus

from sightengine.client import SightengineClient
from Nia.utils import SUDO_USERS as SUDOERS
from Nia.plugins.Telegraph import get_url

import requests
import os
import re

# ---------------- DB ---------------- #

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

# ---------------- API KEYS ---------------- #

api_credentials = [
    {'api_user': '1901288204', 'api_secret': '5PMkvUfRQq6M4BaoZeorD54FSkH6UiKT'},
    {'api_user': '1769346709', 'api_secret': 'UeGqP5mGQjKyuhvokLMC8SZ97XSr5Aoo'},
    {'api_user': '889764613', 'api_secret': '2AFdswWpMMreJnCKn6geB3Yh9qQjZnKm'},
    {'api_user': '359176100', 'api_secret': '3VWntaGo5RcXAYmBSStMY2g35cJ6S3cC'},
]

# ---------------- CACHE ---------------- #

async def load_caches():
    global nsfw_cache, nsfw_block_cache, nsfw_ignore_cache, LOAD

    if LOAD:
        return

    LOAD = True

    nsfw_cache.clear()
    nsfw_block_cache.clear()
    nsfw_ignore_cache.clear()

    try:
        shutil.rmtree("downloads")
        shutil.rmtree("raw_files")
    except:
        pass

    try:
        nsfw_cache = await nsfw_db.find().to_list(None)
        nsfw_block_cache = await nsfw_block_db.find().to_list(None)
        nsfw_ignore_cache = await nsfw_ignore_db.find().to_list(None)
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

@Client.on_message(
    filters.command("nsfwcheck", prefixes=[".", "/"]) & ~filters.edited,
    group=0
)
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

# ---------------- REVIEW ---------------- #

async def take_review(client, message, action):
    REVIEW_CHANNEL = -1002603449066

    try:
        if message.photo:
            await client.send_photo(REVIEW_CHANNEL, message.photo.file_id, caption=action)
        elif message.video:
            await client.send_video(REVIEW_CHANNEL, message.video.file_id, caption=action)
        elif message.animation:
            await client.send_animation(REVIEW_CHANNEL, message.animation.file_id, caption=action)
        elif message.sticker:
            await client.send_sticker(REVIEW_CHANNEL, message.sticker.file_id)
    except Exception as e:
        print("Review error:", e)

# ---------------- ACTION ---------------- #

async def take_action(client, message):
    try:
        await message.delete()
        await message.reply_text("🚫 NSFW detected, action taken")
    except:
        pass

# ---------------- CHECK PHOTO ---------------- #

async def check_nsfw_photo(client, message):

    status = await get_nsfw_status(message.chat.id, client.me.id)
    if status == "disabled":
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

            if data.get("status") != "success":
                continue

            if data.get("nudity", {}).get("sexual_activity", 0) > 0.4:
                await take_review(client, message, "blocked")
                return await take_action(client, message)

            return
        except:
            continue

# ---------------- CHECK VIDEO ---------------- #

async def check_nsfw_video(client, message):

    status = await get_nsfw_status(message.chat.id, client.me.id)
    if status == "disabled":
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

@Client.on_message(filters.command("blockpack") & SUDOERS, group=0)
async def block_pack_handler(client: Client, message: Message):

    target_id = None

    if message.reply_to_message:
        msg = message.reply_to_message
        if msg.sticker:
            target_id = msg.sticker.set_name
        elif msg.photo:
            target_id = msg.photo.file_unique_id
        elif msg.video:
            target_id = msg.video.file_unique_id

    elif len(message.command) > 1:
        target_id = message.command[1]

    if not target_id:
        return await message.reply("Reply ya ID do")

    await nsfw_block_db.insert_one({"file_id": target_id})
    await nsfw_ignore_db.delete_many({"file_id": target_id})
    await message.reply_text(f"Blocked ✅ `{target_id}`")
    await load_caches()

# ---------------- UNBLOCK ---------------- #

@Client.on_message(filters.command("unblockpack") & SUDOERS, group=0)
async def unblock_pack_handler(client: Client, message: Message):

    target_id = None

    if message.reply_to_message:
        msg = message.reply_to_message
        if msg.sticker:
            target_id = msg.sticker.set_name
        elif msg.photo:
            target_id = msg.photo.file_unique_id
        elif msg.video:
            target_id = msg.video.file_unique_id

    elif len(message.command) > 1:
        target_id = message.command[1]

    if not target_id:
        return await message.reply("Reply ya ID do")

    await nsfw_ignore_db.insert_one({"file_id": target_id})
    await nsfw_block_db.delete_many({"file_id": target_id})
    await message.reply_text(f"Unblocked ✅ `{target_id}`")
    await load_caches()

# ---------------- MAIN ---------------- #

@Client.on_message(
    filters.incoming & ~filters.command(["nsfwcheck", "blockpack", "unblockpack"]),
    group=1
)
async def nsfws(client: Client, message: Message):

    if not nsfw_cache:
        await load_caches()

    if message.photo or message.sticker:
        asyncio.create_task(check_nsfw_photo(client, message))

    elif message.video or message.animation:
        asyncio.create_task(check_nsfw_video(client, message))
