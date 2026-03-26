# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar 
#
# All rights reserved.
#
# This code is the intellectual property of @WTF_Phantom.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: king25258069@gmail.com

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatType
from Nia.plugins.chatbot import ask_mistral_raw
from Nia.database import riddles_collection, users_collection
from Nia.utils import format_money, ensure_user_exists, get_mention
from Nia.config import RIDDLE_REWARD

async def riddle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts a new AI riddle."""
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE: return await update.message.reply_text("❌ Group Only!", parse_mode=ParseMode.HTML)

    # Check active riddle
    if riddles_collection.find_one({"chat_id": chat.id}):
        return await update.message.reply_text("⚠️ A riddle is already active! Guess it.", parse_mode=ParseMode.HTML)

    msg = await update.message.reply_text("🧠 <b>Generating AI Riddle...</b>", parse_mode=ParseMode.HTML)

    # Generate
    prompt = "Generate a short, hard riddle. Format: 'Riddle: [Question] | Answer: [OneWordAnswer]'. Do not add anything else."
    response = await ask_mistral_raw(system_prompt="You are a Riddle Master.", user_input=prompt)
    
    if not response or "|" not in response:
        return await msg.edit_text("⚠️ AI Brain Freeze. Try again.", parse_mode=ParseMode.HTML)

    try:
        parts = response.split("|")
        question = parts[0].replace("Riddle:", "").strip()
        answer = parts[1].replace("Answer:", "").strip().lower()
    except:
        return await msg.edit_text("⚠️ AI Error.", parse_mode=ParseMode.HTML)

    # Save
    riddles_collection.insert_one({"chat_id": chat.id, "answer": answer})

    await msg.edit_text(
        f"🧩 <b>𝐀𝐈 𝐑𝐢𝐝𝐝𝐥𝐞 𝐂𝐡𝐚𝐥𝐥𝐞𝐧𝐠𝐞!</b>\n\n"
        f"<i>{question}</i>\n\n"
        f"💡 <b>Reward:</b> <code>{format_money(RIDDLE_REWARD)}</code>\n"
        f"👇 <i>Reply with your answer!</i>",
        parse_mode=ParseMode.HTML
    )

async def check_riddle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks user messages for the answer."""
    if not update.message or not update.message.text: return
    chat = update.effective_chat
    text = update.message.text.strip().lower()

    riddle = riddles_collection.find_one({"chat_id": chat.id})
    if not riddle: return

    if text == riddle['answer']:
        user = update.effective_user
        ensure_user_exists(user)
        
        # Winner
        users_collection.update_one({"user_id": user.id}, {"$inc": {"balance": RIDDLE_REWARD}})
        riddles_collection.delete_one({"chat_id": chat.id})
        
        await update.message.reply_text(
            f"🎉 <b>𝐂𝐨𝐫𝐫𝐞𝐜𝐭!</b>\n\n"
            f"👤 <b>Winner:</b> {get_mention(user)}\n"
            f"💰 <b>Won:</b> <code>{format_money(RIDDLE_REWARD)}</code>\n"
            f"🔑 <b>Answer:</b> <i>{riddle['answer'].title()}</i>",
            parse_mode=ParseMode.HTML
        )
