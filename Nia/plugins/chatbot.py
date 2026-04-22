# ----- FAST HUMAN FRIENDLY CHATBOT -----

import httpx
import random
import urllib.parse
import shutil
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ChatType

from Nia.database import chatbot_collection
# ❌ stylize_text removed
import random
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatMemberStatus as CMS, ChatMembersFilter
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, VideoChatScheduled
from Nia.plugins.Telegraph import get_url
from sightengine.client import SightengineClient
from Nia.utils import SUDO_USERS as SUDOERS
import re
import os
import aiohttp
import asyncio
import json

NSFW = MongoCli("mongodb+srv://nsfwstorage:a@cluster0.c3iqn53.mongodb.net/?appName=Cluster0")
stats_db = NSFW.Anonymous #(STORES ON/OFF SETTINGS OF GC)
nsfw_storage = NSFW.STORAGE #(STORES ON/OFF SETTINGS OF GC)
nsfw_db = stats_db.nsfw_check.status #(CHECK STATUS ON/OFF OF GC)
nsfw_block_db = nsfw_storage.nsfw_block.sticker #(STORES BAD STICKERS)
nsfw_ignore_db = nsfw_storage.nsfw_ignore.sticker #(STORES GOOD STICKERS)

nsfw_cache = []
nsfw_block_cache = []
nsfw_ignore_cache = []

LOAD = "FALSE"

async def load_caches():
    global nsfw_ignore_cache, nsfw_cache, nsfw_block_cache, LOAD
    if LOAD == "TRUE":
        return
    LOAD = "TRUE"
    nsfw_cache.clear()
    nsfw_block_cache.clear()
    nsfw_ignore_cache.clear()
    
    try:
        shutil.rmtree("downloads")
        shutil.rmtree("raw_files")
        
    except:
        pass
    print("All cache cleaned ✅")
    try:
        print("Loading All Caches...")
        
        nsfw_cache = await nsfw_db.find().to_list(length=None)
        print(f"{len(nsfw_cache)} Nsfw Cache Loaded ✅")
        nsfw_block_cache = await nsfw_block_db.find().to_list(length=None)
        print(f"{len(nsfw_block_cache)} NSFW blocklist loaded ✅")
        nsfw_ignore_cache = await nsfw_ignore_db.find().to_list(length=None)
        print(f"{len(nsfw_ignore_cache)} NSFW ignore list Loaded ✅")
       
        print("All caches loaded 👍 ✅")
        LOAD = "FALSE"
    except Exception as e:
        print(f"Error loading caches: {e}")
        LOAD = "FALSE"
    return

async def get_nsfw_status_from_cache(chat_id: int, bot_id: int):
    for data in nsfw_cache:
        if data.get("chat_id") == chat_id and data.get("bot_id") == bot_id:
            return data.get("status", "enabled")
    return "enabled"


async def check_delete_permission(client: Client, message: Message) -> bool:
    try:
        chat = await client.get_chat(message.chat.id)
        
        admin = await client.get_chat_member(chat.id, client.me.id)
        return admin.privileges.can_delete_messages if admin.privileges else False
        
    except Exception:
        return False

async def check_restrict_permission(client: Client, message: Message) -> bool:
    try:
        chat = await client.get_chat(message.chat.id)
            
        admin = await client.get_chat_member(chat.id, client.me.id)
        return admin.privileges.can_restrict_members if admin.privileges else False
        
    except Exception:
        return False

async def is_admin(client, chat_id, user_id):
    try:
        admin_ids = [
            admin.user.id
            async for admin in client.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            )
        ]
        if user_id in admin_ids or user_id == chat_id or user_id in SUDOERS:
            return True
        return False
    except Exception:
        if user_id == chat_id or user_id in SUDOERS:
            return True
        return False


@Client.on_message(filters.command("nsfwcheck", prefixes=[".", "/"]))
async def nsfw_command(client: Client, message: Message):
    command = message.text.split()
    if len(command) > 1:
        flag = command[1].lower()
        chat_id = message.chat.id
        bot_id = client.me.id
        user = message.from_user
        user_id = user.id
        
        admin = await is_admin(client, chat_id, user_id)

        if not admin and not chat_id == user_id and not user_id == bot_id:
            msg = await message.reply_text("**ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ 😶. ᴄᴏɴᴛᴀᴄᴛ ᴀɴ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ɴꜱғᴡ sᴇᴛᴛɪɴɢꜱ.**")
            await asyncio.sleep(8)
            return await msg.delete()
        
        if flag in ["on", "enable"]:
            nsfw_db.update_one(
                {"chat_id": chat_id, "bot_id": bot_id},
                {"$set": {"status": "enabled"}},
                upsert=True
            )
            await message.reply_text("NSFW Content check has been **enabled** for this chat ✅.")
            await load_caches()
        
        elif flag in ["off", "disable"]:
            member = await client.get_chat_member(chat_id, user_id)
            
            if member.status == ChatMemberStatus.OWNER:
                nsfw_db.update_one(
                    {"chat_id": chat_id, "bot_id": bot_id},
                    {"$set": {"status": "disabled"}},
                    upsert=True
                )
                await message.reply_text("NSFW Content check has been **disabled** for this chat ❌.")
                await load_caches()
            else:
                owner = None
                async for member in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
                    if member.status == ChatMemberStatus.OWNER:
                        owner = member
                        break
                
                if not owner or not owner.user or owner.user.is_deleted or owner.user.status == "long_ago":
                    if admin:
                        nsfw_db.update_one(
                            {"chat_id": chat_id, "bot_id": bot_id},
                            {"$set": {"status": "disabled"}},
                            upsert=True
                        )
                        await message.reply_text("Group owner not available. NSFW check disabled by admin.")
                        await load_caches()
                    else:
                        await message.reply_text("Only the group owner can disable NSFW check ❌.")
                else:
                    await message.reply_text("Only the group owner can disable NSFW check ❌.")
        
        else:
            await message.reply_text("Invalid option! Use `/nsfwcheck on` or `/nsfwcheck off`.")
    else:
        await message.reply_text(
            "Please specify an option to enable or disable the nsfw check\n\n"
            "Example: `/nsfwcheck on` or `/nsfwcheck off`"
        )
        

@Client.on_callback_query(filters.regex(r"^(blockpack|unblockpack|approve)$"))
async def review_callback_handler(client, callback_query: CallbackQuery):
    global nsfw_block_db, nsfw_ignore_db
    
    action = callback_query.data 
    caption = callback_query.message.caption or callback_query.message.text or None
    
    if not caption:
        return await callback_query.answer("⚠️ No caption found !", show_alert=True)

    target_id = None
    if "ID=" in caption:
        target_id = caption.split("ID=")[1].strip()

    if not target_id:
        return await callback_query.answer("⚠️ Cannot detect target ID from caption!", show_alert=True)
    
    if action == "unblockpack":
        await nsfw_ignore_db.insert_one({"file_id": target_id})
        await nsfw_block_db.delete_many({"file_id": target_id})
        await callback_query.answer(f"Ok Content Unblocked ❌\n\nID = {target_id}", show_alert=False)

    elif action == "blockpack":
        await nsfw_block_db.insert_one({"file_id": target_id})
        await nsfw_ignore_db.delete_many({"file_id": target_id})
        await callback_query.answer(f"Ok Content Blocked ✅\n\nID = {target_id}", show_alert=False)
        
    elif action == "approve":
        await callback_query.answer("Ok Approved 👍", show_alert=False)

    try:
        await client.edit_message_caption(
            callback_query.message.chat.id,
            callback_query.message.id,
            caption=f"✅ Action completed & {action}.\nId:- `{target_id}`"
        )
        await asyncio.sleep(1.5)
        await client.delete_messages(callback_query.message.chat.id, callback_query.message.id)
    except Exception:
        pass

    



async def take_review(message, action):
    REVIEW_CHANNEL_ID = -1002603449066
    PHOTO_CHANNEL = -1003305583065
    IGNORED_CHANNEL_ID = -1002757059774
    caption_text = ""
    buttons = None
    file_type = None
    file_to_send = None

    if message.sticker and message.sticker.set_name:
        file_type = "sticker"
        file_to_send = message.sticker.file_id
        target_id = message.sticker.set_name
    elif message.photo:
        file_type = "photo"
        file_to_send = await message.download() 
        target_id = message.photo.file_unique_id
    elif message.video:
        file_type = "video"
        file_to_send = await message.download()  
        target_id = message.video.file_unique_id
    elif message.animation:
        file_type = "animation"
        file_to_send = await message.download()  
        target_id = message.animation.file_unique_id
   

    if action == "blocked":
        caption_text = f"**This content has been BLOCKED 🚫**\n\nDo you want to Unblock it?\n\n**ID=** `{target_id}`"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Unblock ❌", callback_data="unblockpack"),
                InlineKeyboardButton("Block 🚫", callback_data="blockpack")
            ]
        ])
        try:
            if file_type == "photo":
                await nexichat.send_photo(PHOTO_CHANNEL, file_to_send, caption=caption_text, reply_markup=buttons)
            elif file_type == "video":
                await nexichat.send_video(PHOTO_CHANNEL, file_to_send, caption=caption_text, reply_markup=buttons)
            elif file_type == "animation":
                await nexichat.send_animation(PHOTO_CHANNEL, file_to_send, caption=caption_text, reply_markup=buttons)
            elif file_type == "sticker":
                sent_msg = await nexichat.send_sticker(REVIEW_CHANNEL_ID, file_to_send)
                await asyncio.sleep(1)
                await nexichat.send_message(
                    REVIEW_CHANNEL_ID,
                    caption_text,
                    reply_to_message_id=sent_msg.id,
                    reply_markup=buttons
                )
        except Exception as e:
            print(f"❌ Review bhejne me error aaya:\n`{e}`")

    elif action == "ignore":
        caption_text = f"**This content has been PASSED ✅**\n\nDo you want to Block it?\n\n**ID=** `{target_id}`"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Block 🚫", callback_data="blockpack"),
                InlineKeyboardButton("Unblock ❌", callback_data="unblockpack")
            ]
        ])
        try:
            # if file_type == "photo":
            #     await nexichat.send_photo(IGNORED_CHANNEL_ID, file_to_send, caption=caption_text, reply_markup=buttons)
            # elif file_type == "video":
            #     await nexichat.send_video(IGNORED_CHANNEL_ID, file_to_send, caption=caption_text, reply_markup=buttons)
            # elif file_type == "animation":
            #     await nexichat.send_animation(IGNORED_CHANNEL_ID, file_to_send, caption=caption_text, reply_markup=buttons)
            if file_type == "sticker":
                sent_msg = await nexichat.send_sticker(IGNORED_CHANNEL_ID, file_to_send)
                await asyncio.sleep(1)
                await nexichat.send_message(
                    IGNORED_CHANNEL_ID,
                    caption_text,
                    reply_to_message_id=sent_msg.id,
                    reply_markup=buttons
                )
        except Exception as e:
            print(f"❌ Review bhejne me error aaya:\n`{e}`")


async def take_action(client, message):
    try:
        try:
            await message.delete()
            name = "ᴀ ᴜꜱᴇʀ"
            try:
                if message.from_user:
                    name = message.from_user.mention
                elif message.sender_chat:
                    name = message.sender_chat.title or "ᴀ ᴄʜᴀɴɴᴇʟ/ᴀᴅᴍɪɴ"
            except:
                pass
            ok = await message.reply_text(f"**{name} ꜱᴇɴᴛ ɴꜱꜰᴡ-ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ, ᴛᴀᴋɪɴɢ ᴀᴄᴛɪᴏɴ...**")
        except:
            pass
    
        message_id = message.id
        chat_id = message.chat.id
        admins = [
            admin.user.id
            async for admin in client.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            )
        ]
        text = "🥵"
        for admin in admins:
            admin_member = await client.get_chat_member(chat_id, admin)
            if not admin_member.user.is_bot and not admin_member.user.is_deleted:
                text += f"[\u2063](tg://user?id={admin})"
              
        message_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message_id}"
        can_delete = await check_delete_permission(client, message)
        can_restrict = await check_restrict_permission(client, message)
        
        report_msg = f"**🚫 NSFW Media Detected {text}**\n\n"
        report_msg += f"** • Sᴇɴᴛ Bʏ »** {name}\n"
        user_id = f"{message.from_user.id}" if message.from_user else "No ID"
        report_msg += f"** • Uꜱᴇʀ ɪᴅ »** `{user_id}`\n\n"

        if can_delete:
            report_msg += "✅ 𝙸'ᴠᴇ **ᴅᴇʟᴇᴛᴇᴅ** ᴛʜᴀᴛ ᴍᴇᴅɪᴀ.\n"
        else:
            report_msg += "👉 ɢɪᴠᴇ ᴍᴇ **'ᴅᴇʟᴇᴛᴇ ᴍꜱɢ'** ᴩᴏᴡᴇʀ ᴛᴏ ᴄʟᴇᴀɴ.\n"
        
        if can_restrict:
            try:
                await message.chat.restrict_member(message.from_user.id, permissions=ChatPermissions())
                report_msg += "✅ 𝙸'ᴠᴇ **ᴍᴜᴛᴇᴅ** ᴛʜᴀᴛ ᴜꜱᴇʀ."
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔊 ᴜɴᴍᴜᴛᴇ ᴜꜱᴇʀ", 
                        callback_data=f"unmute_{message.from_user.id}"
                    )
                ]])
            except Exception as e:
                keyboard = None
        else:
            report_msg += f"👉 ɢɪᴠᴇ ᴍᴇ **'ʙᴀɴ ᴩᴏᴡᴇʀ'** ᴛᴏ ᴍᴜᴛᴇ ᴜꜱᴇʀ."
            keyboard = None
        
        report_msg += f"\n\n||🚨 Uꜱᴇ: /nsfwcheck [ ᴏɴ/ᴏꜰꜰ ]||"
        await message.reply_text(
            report_msg,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        await ok.delete()
        return True
        
    except Exception as e:
        message_id = message.id
        chat_id = message.chat.id
        admins = [
            admin.user.id
            async for admin in client.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            )
        ]
        text = "🥵"
        for admin in admins:
            admin_member = await client.get_chat_member(chat_id, admin)
            if not admin_member.user.is_bot and not admin_member.user.is_deleted:
                text += f"[\u2063](tg://user?id={admin})"
              
        await message.reply_text(f"**{message.from_user.mention} sending nsfw/18+ content{text}, make me admin to delete that**")
        return



api_credentials = [
    {'api_user': '1901288204', 'api_secret': '5PMkvUfRQq6M4BaoZeorD54FSkH6UiKT'},
    {'api_user': '1769346709', 'api_secret': 'UeGqP5mGQjKyuhvokLMC8SZ97XSr5Aoo'},
    {'api_user': '889764613', 'api_secret': '2AFdswWpMMreJnCKn6geB3Yh9qQjZnKm'},
    {'api_user': '359176100', 'api_secret': '3VWntaGo5RcXAYmBSStMY2g35cJ6S3cC'}, 
    
]

async def check_nsfw_photo(client, message):
    global nsfw_block_cache, nsfw_ignore_cache
    chat_id = message.chat.id
    bot_id = client.me.id
    nsfw_status = await get_nsfw_status_from_cache(chat_id, bot_id)
    if nsfw_status and nsfw_status == "disabled":
        return

    if message.sticker and message.sticker.set_name:
        file_id = message.sticker.set_name
        for entry in nsfw_block_cache:
            if entry.get("file_id") == file_id:
                return await take_action(client, message)
        for entry in nsfw_ignore_cache:
            if entry.get("file_id") == file_id:
                return

    elif message.photo:
        file_id = message.photo.file_unique_id
        for entry in nsfw_block_cache:
            if entry.get("file_id") == file_id:
                return await take_action(client, message)
        for entry in nsfw_ignore_cache:
            if entry.get("file_id") == file_id:
                return

    url = await get_url(client, message)

    creds = random.choice(api_credentials)
    params = {
        'url': url,
        'models': 'nudity-2.1',
        'api_user': creds['api_user'],
        'api_secret': creds['api_secret']
    }

    try:
        r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
        output = json.loads(r.text)

        if output.get("status") != "success":
            return False

        nudity = output.get("nudity", {})
        sexual_scores = [
            nudity.get("sexual_activity", 0),
            nudity.get("sexual_display", 0),
            nudity.get("erotica", 0),
            nudity.get("very_suggestive", 0),
            nudity.get("suggestive", 0),
            nudity.get("mildly_suggestive", 0)
        ]

        if any(score > 0.4 for score in sexual_scores):
            if message.sticker and message.sticker.set_name:
                file_id = message.sticker.set_name
                await nsfw_block_db.insert_one({"file_id": file_id})
                nsfw_block_cache.append({"file_id": file_id})
                action = "blocked"
                await take_review(message, action)
            elif message.photo:
                file_id = message.photo.file_unique_id
                await nsfw_block_db.insert_one({"file_id": file_id})
                nsfw_block_cache.append({"file_id": file_id})
                action = "blocked"
                await take_review(message, action)
            return await take_action(client, message)
        else:
            if message.sticker and message.sticker.set_name:
                file_id = message.sticker.set_name
                await nsfw_ignore_db.insert_one({"file_id": file_id})
                nsfw_ignore_cache.append({"file_id": file_id})
                action = "ignore"
                await take_review(message, action)
            elif message.photo:
                file_id = message.photo.file_unique_id
                await nsfw_ignore_db.insert_one({"file_id": file_id})
                nsfw_ignore_cache.append({"file_id": file_id})
                action = "ignore"
                await take_review(message, action)
            return

    except Exception as e:
        return False



async def check_nsfw_video(client, message):
    global nsfw_block_cache, nsfw_ignore_cache, nsfw_ignore_db, nsfw_block_db
    chat_id = message.chat.id
    bot_id = client.me.id
    nsfw_status = await get_nsfw_status_from_cache(chat_id, bot_id)
    if nsfw_status and nsfw_status == "disabled":
        return

    if message.sticker and message.sticker.set_name:
        file_id = message.sticker.set_name
        for entry in nsfw_block_cache:
            if entry.get("file_id") == file_id:
                return await take_action(client, message)
        for entry in nsfw_ignore_cache:
            if entry.get("file_id") == file_id:
                return

    elif message.animation:
        file_id = message.animation.file_unique_id
        for entry in nsfw_block_cache:
            if entry.get("file_id") == file_id:
                return await take_action(client, message)
        for entry in nsfw_ignore_cache:
            if entry.get("file_id") == file_id:
                return

    elif message.video:
        file_id = message.video.file_unique_id
        for entry in nsfw_block_cache:
            if entry.get("file_id") == file_id:
                return await take_action(client, message)
        for entry in nsfw_ignore_cache:
            if entry.get("file_id") == file_id:
                return

    try:
        video_url = await get_url(client, message)

        creds = random.choice(api_credentials)
        se_client = SightengineClient(creds['api_user'], creds['api_secret'])

        output = se_client.check('nudity-2.1').video_sync(video_url)
        frames = output.get('data', {}).get('frames', [])

        for frame in frames:
            nudity = frame.get('nudity', {})
            if nudity:
                if (
                    nudity.get('sexual_activity', 0) > 0.1 or
                    nudity.get('sexual_display', 0) > 0.1 or
                    nudity.get('erotica', 0) > 0.1 or
                    nudity.get('sextoy', 0) > 0.1 or
                    nudity.get('suggestive', 0) > 0.1
                ):
                    if message.sticker and message.sticker.set_name:
                        file_id = message.sticker.set_name
                        await nsfw_block_db.insert_one({"file_id": file_id})
                        nsfw_block_cache.append({"file_id": file_id})
                        action = "blocked"
                        await take_review(message, action)
                    elif message.animation:
                        file_id = message.animation.file_unique_id
                        await nsfw_block_db.insert_one({"file_id": file_id})
                        nsfw_block_cache.append({"file_id": file_id})
                        action = "blocked"
                        await take_review(message, action)
                    elif message.video:
                        file_id = message.video.file_unique_id
                        await nsfw_block_db.insert_one({"file_id": file_id})
                        nsfw_block_cache.append({"file_id": file_id})
                        action = "blocked"
                        await take_review(message, action)
                    return await take_action(client, message)
                else:
                    if message.sticker and message.sticker.set_name:
                        file_id = message.sticker.set_name
                        await nsfw_ignore_db.insert_one({"file_id": file_id})
                        nsfw_ignore_cache.append({"file_id": file_id})
                        action = "ignore"
                        await take_review(message, action)
                    elif message.animation:
                        file_id = message.animation.file_unique_id
                        await nsfw_ignore_db.insert_one({"file_id": file_id})
                        nsfw_ignore_cache.append({"file_id": file_id})
                        action = "ignore"
                        await take_review(message, action)
                    elif message.video:
                        file_id = message.video.file_unique_id
                        await nsfw_ignore_db.insert_one({"file_id": file_id})
                        nsfw_ignore_cache.append({"file_id": file_id})
                        action = "ignore"
                        await take_review(message, action)
                    return
        return

    except Exception as e:
        print(f"Error processing video: {e}")
        return

@Client.on_message(filters.command("blockpack") & SUDOERS)
async def block_pack_handler(client: Client, message: Message):
    global nsfw_block_db, nsfw_ignore_db
    target_id = None

    if message.reply_to_message:
        msg = message.reply_to_message
        if msg.sticker and msg.sticker.set_name:
            target_id = msg.sticker.set_name
            
        elif msg.photo:
            target_id = msg.photo.file_unique_id
        elif msg.video:
            target_id = msg.video.file_unique_id
        elif msg.animation:
            target_id = msg.animation.file_unique_id

    elif len(message.command) > 1:
        target_id = message.command[1]
        
    if not target_id:
        return await message.reply("⚠️ Kuch bhi block karne ke liye reply karo ya ek valid ID do.")

    await nsfw_block_db.insert_one({"file_id": target_id})
    await nsfw_ignore_db.delete_many({"file_id": target_id})
    await message.reply_text(f"**Blocked content ✅**:- `{target_id}`")
    action = "blocked"
    await take_review(message, action)
    await load_caches()

@Client.on_message(filters.command("unblockpack") & SUDOERS)
async def unblock_pack_handler(client: Client, message: Message):
    global nsfw_block_db, nsfw_ignore_db
    target_id = None
    
    if message.reply_to_message:
        msg = message.reply_to_message
        if msg.sticker and msg.sticker.set_name:
            target_id = msg.sticker.set_name
            
        elif msg.photo:
            target_id = msg.photo.file_unique_id
        elif msg.video:
            target_id = msg.video.file_unique_id
        elif msg.animation:
            target_id = msg.animation.file_unique_id

    elif len(message.command) > 1:
        target_id = message.command[1]

    if not target_id:
        return await message.reply("⚠️ Kuch bhi unblock karne ke liye reply karo ya ek valid ID do.")

    await nsfw_ignore_db.insert_one({"file_id": target_id})
    await nsfw_block_db.delete_many({"file_id": target_id})
    await message.reply_text(f"**Unblocked content ✅**:- `{target_id}`")
    action = "ignore"
    await take_review(message, action)
    await load_caches()
   
# -------- SETTINGS --------

API_URL = "https://stdgpt.vercel.app/?text="

MAX_HISTORY = 6

FALLBACK_RESPONSES = [
    "acha sahi 🙂",
    "haan yaar",
    "lol 😅",
    "samjha",
    "acha fir",
]


# -------- HUMAN STYLE PROMPT --------

SYSTEM_PROMPT = """
You are a friendly Indian chat partner.

Rules:
- Talk like a normal human
- Use Hinglish (Hindi + English)
- Replies must be short
- 1 sentence mostly
- Talk casual like WhatsApp chat
- No long explanations
- Sometimes use emojis 🙂

Examples:

User: kaisa hai
Bot: me badhiya hu 🙂 tu bata

User: kya kar raha
Bot: kuch nahi yaar bas timepass

User: bore ho raha
Bot: same yaar 😅 chal baat karte
"""


# -------- SPEED OPTIMIZATION --------

http_client = httpx.AsyncClient(timeout=5)
AI_CACHE = {}


# -------- AI CORE --------

async def get_ai_reply(chat_id, user_text):

    if user_text in AI_CACHE:
        return AI_CACHE[user_text]

    doc = chatbot_collection.find_one({"chat_id": chat_id}) or {}
    history = doc.get("history", [])

    prompt = SYSTEM_PROMPT + "\nUser: " + user_text + "\nBot:"
    encoded = urllib.parse.quote(prompt)
    url = f"{API_URL}{encoded}"

    try:
        resp = await http_client.get(url)

        if resp.status_code != 200:
            return random.choice(FALLBACK_RESPONSES)

        data = resp.json()

        if "reply" in data:
            reply = data["reply"]

        elif "response" in data:
            reply = data["response"]

        elif "answer" in data:
            reply = data["answer"]

        elif "message" in data:
            reply = data["message"]

        else:
            reply = str(data)

    except:
        return random.choice(FALLBACK_RESPONSES)

    reply = reply.strip()

    AI_CACHE[user_text] = reply

    new_history = history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": reply}
    ]

    if len(new_history) > MAX_HISTORY * 2:
        new_history = new_history[-MAX_HISTORY * 2:]

    chatbot_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"history": new_history}},
        upsert=True
    )

    return reply


# -------- MESSAGE HANDLER --------

async def ai_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message

    if not msg or not msg.text:
        return

    # ❌ bot to bot ignore
    if msg.from_user and msg.from_user.is_bot:
        return

    text = msg.text.strip()

    if text.startswith("/"):
        return

    chat = update.effective_chat
    should_reply = False

    # ---- PRIVATE ----
    if chat.type == ChatType.PRIVATE:
        should_reply = True

    # ---- GROUP ----
    elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:

        bot_username = (context.bot.username or "").lower()

        if msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id:
            should_reply = True

        elif f"@{bot_username}" in text.lower():
            should_reply = True
            text = text.replace(f"@{bot_username}", "").strip()

        elif text.lower().startswith(("hiii", "heeey", "hellllo", "niaaa", "oyeee", "suuun")):
            should_reply = True

    if not should_reply:
        return

    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)

    reply = await get_ai_reply(chat.id, text)

    # ✅ directly reply (no stylize)
    await msg.reply_text(reply)


# -------- ECONOMY SUPPORT --------

async def ask_mistral_raw(system_prompt, user_input, max_tokens=150):

    prompt = system_prompt + "\nUser: " + user_input + "\nBot:"
    encoded = urllib.parse.quote(prompt)
    url = f"{API_URL}{encoded}"

    try:
        resp = await http_client.get(url)

        if resp.status_code != 200:
            return None

        data = resp.json()

        if "reply" in data:
            return data["reply"]

        elif "response" in data:
            return data["response"]

        elif "answer" in data:
            return data["answer"]

        elif "message" in data:
            return data["message"]

        else:
            return str(data)

    except:
        return None


# -------- COMMANDS --------

async def chatbot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 AI Chatbot Active\n\n"
        "Mujhse normal chat karo 🙂"
    )


async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use: /ask kya kar raha")
        return

    text = " ".join(context.args)

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    reply = await get_ai_reply(update.effective_chat.id, text)

    # ✅ no stylize here too
    await update.message.reply_text(reply)

@Client.on_message(filters.incoming, group=1)
async def nsfws(client: Client, message: Message):
    global nsfw_block_cache
    if not nsfw_block_cache:
        await load_caches()

    if (message.sticker or message.photo) and (message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]):
        asyncio.create_task(check_nsfw_photo(client, message))
    if (message.animation or message.video) and (message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]):
        asyncio.create_task(check_nsfw_video(client, message))
    
