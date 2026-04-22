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

import os
# --- CRITICAL FIX: MUST BE AT THE VERY TOP ---
os.environ["GIT_PYTHON_REFRESH"] = "quiet"
# ---------------------------------------------

from threading import Thread
from flask import Flask
from telegram import Update 
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    ChatMemberHandler, MessageHandler, filters
)
from telegram.request import HTTPXRequest

# --- INTERNAL IMPORTS ---
from Nia.config import TOKEN, PORT
from Nia.utils import log_to_channel, BOT_NAME
# Import all plugins
from Nia.plugins import start, economy, game, admin, broadcast, fun, Telegraph, events, welcome, ping, chatbot, riddle, social, ai_media, waifu, collection, shop, daily

# --- FLASK SERVER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Alive"

def run_flask(): 
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# --- STARTUP LOGIC ---
async def post_init(application):
    print("✅ ʙᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ! ꜱᴇᴛᴛɪɴɢ ᴍᴇɴᴜ ᴄᴏᴍᴍᴀɴᴅꜱ ᴡᴀɪᴛ ᴋʀ ʟᴀᴜᴅᴇ🪽...")
    
    # --- PUBLIC MENU (Admin commands hidden) ---
    await application.bot.set_my_commands([
        ("start", "🌸 ϻᴧɪη ϻєηυ"), 
        ("help", "📖 ᴄσϻϻᴧηᴅ ᴅɪᴧꝛʏ"),
        ("bal", "👛 ᴡᴧʟʟєᴛ"), 
        ("shop", "🛒 sʜσᴘ"),
        ("kill", "🔪 ᴋɪʟʟ"), 
        ("rob", "💰 sᴛєᴧʟ"), 
        ("give", "💸 ᴛꝛᴧηsғєꝛ"), 
        ("claim", "💎 ʙσηυs"),
        ("daily", "📅 ᴅᴧɪʟʏ"), 
        ("ranking", "🏆 ᴛσᴘs"),
        ("propose", "💍 ϻᴧꝛꝛʏ"), 
        ("divorce", "💔 ʙꝛєᴧᴋυᴘ"),
        ("wpropose", "👰 ᴡᴧɪғυ"), 
        ("draw", "🎨 ᴧꝛᴛ"),
        ("speak", "🗣️ νσɪᴄє"), 
        ("chatbot", "🧠 ᴧɪ"),
        ("ping", "📶 sᴛᴧᴛυs")
    ])
    
    try:
        bot_info = await application.bot.get_me()
        print(f"✅ Logged in as {bot_info.username} 𝐀ʙ 𝐃ᴇᴛᴏx 𝐊ᴏ 𝐀ᴩɴɪ 𝐆𝐅 кι ¢нυт ᴅᴇᴛᴀ ᴊᴀᴀ😎🥀")
        await log_to_channel(application.bot, "start", {
            "user": "System", 
            "chat": "Cloud Server",
            "action": f"{BOT_NAME} (@{bot_info.username}) is now Online! 🚀"
        })
    except Exception as e:
        print(f"⚠️ Startup Log Failed: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Start Web Server
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    if not TOKEN:
        print("CRITICAL: BOT_TOKEN is missing.")
    else:
        # 2. Configure Network
        t_request = HTTPXRequest(connection_pool_size=16, connect_timeout=60.0, read_timeout=60.0)
        app_bot = ApplicationBuilder().token(TOKEN).request(t_request).post_init(post_init).build()

        # --- REGISTER HANDLERS ---
        
        # Basics
        app_bot.add_handler(CommandHandler("start", start.start))
        app_bot.add_handler(CommandHandler("help", start.help_command))
        app_bot.add_handler(CommandHandler("ping", ping.ping))
        app_bot.add_handler(CallbackQueryHandler(ping.ping_callback, pattern="^sys_stats$"))
        app_bot.add_handler(CallbackQueryHandler(start.help_callback, pattern="^help_"))
        app_bot.add_handler(CallbackQueryHandler(start.help_callback, pattern="^return_start$"))
        
        # Economy
        app_bot.add_handler(CommandHandler("register", economy.register))
        app_bot.add_handler(CommandHandler("bal", economy.balance))
        app_bot.add_handler(CallbackQueryHandler(economy.inventory_callback, pattern="^inv_"))
        app_bot.add_handler(CommandHandler("ranking", economy.ranking))
        app_bot.add_handler(CommandHandler("give", economy.give))
        app_bot.add_handler(CommandHandler("claim", economy.claim))
        app_bot.add_handler(CommandHandler("daily", daily.daily))
        
        # Shop
        app_bot.add_handler(CommandHandler("shop", shop.shop_menu))
        app_bot.add_handler(CommandHandler("buy", shop.buy))
        app_bot.add_handler(CallbackQueryHandler(shop.shop_callback, pattern="^shop_"))
        
        # RPG / Game
        app_bot.add_handler(CommandHandler("kill", game.kill))
        app_bot.add_handler(CommandHandler("rob", game.rob))
        app_bot.add_handler(CommandHandler("protect", game.protect))
        app_bot.add_handler(CommandHandler("revive", game.revive))
        
        # Social / Waifu
        app_bot.add_handler(CommandHandler("propose", social.propose))
        app_bot.add_handler(CommandHandler("marry", social.marry_status))
        app_bot.add_handler(CommandHandler("divorce", social.divorce))
        app_bot.add_handler(CommandHandler("couple", social.couple_game))
        app_bot.add_handler(CallbackQueryHandler(social.proposal_callback, pattern="^marry_"))
        
        app_bot.add_handler(CommandHandler("wpropose", waifu.wpropose))
        app_bot.add_handler(CommandHandler("wmarry", waifu.wmarry))
        for a in waifu.SFW_ACTIONS: app_bot.add_handler(CommandHandler(a, waifu.waifu_action))

        # Fun / AI
        app_bot.add_handler(CommandHandler("dice", fun.dice))
        app_bot.add_handler(CommandHandler("slots", fun.slots))
        app_bot.add_handler(CommandHandler("riddle", riddle.riddle_command))
        app_bot.add_handler(CommandHandler("draw", ai_media.draw_command))
        app_bot.add_handler(CommandHandler("speak", ai_media.speak_command))
        
        # Admin & System
        app_bot.add_handler(CommandHandler("welcome", welcome.welcome_command))
        app_bot.add_handler(CommandHandler("broadcast", broadcast.broadcast))
        app_bot.add_handler(CommandHandler("sudo", admin.sudo_help))
        app_bot.add_handler(CommandHandler("sudolist", admin.sudolist))
        app_bot.add_handler(CommandHandler("addsudo", admin.addsudo))
        app_bot.add_handler(CommandHandler("rmsudo", admin.rmsudo))
        app_bot.add_handler(CommandHandler("addcoins", admin.addcoins))
        app_bot.add_handler(CommandHandler("rmcoins", admin.rmcoins))
        app_bot.add_handler(CommandHandler("freerevive", admin.freerevive))
        app_bot.add_handler(CommandHandler("unprotect", admin.unprotect))
        app_bot.add_handler(CommandHandler("cleandb", admin.cleandb))
        app_bot.add_handler(CommandHandler("update", admin.update_bot))
        app_bot.add_handler(CallbackQueryHandler(admin.confirm_handler, pattern="^cnf\|"))
        
        # Events & Messages (ORDER IS CRITICAL)
        app_bot.add_handler(ChatMemberHandler(events.chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
        app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome.new_member))
        
        # 1. Collection (Waifu Guessing)
        app_bot.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, collection.collect_waifu), group=1)
        # 2. Drop Check (Message Counting)
        app_bot.add_handler(MessageHandler(filters.ChatType.GROUPS, collection.check_drops), group=2)
        # 3. Riddle Answer
        app_bot.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, riddle.check_riddle_answer), group=3)
        # 4. AI Chat
        app_bot.add_handler(MessageHandler((filters.TEXT | filters.Sticker.ALL) & ~filters.COMMAND, chatbot.ai_message_handler), group=4)
        
        # 5. Group Tracking (FIXED: Uses Async function from events.py)
        app_bot.add_handler(MessageHandler(filters.ChatType.GROUPS, events.group_tracker), group=5)

        print("ꝛʏᴧηʙᴧᴋᴧ ʙσᴛ ꜱᴛᴀʀᴛɪɴɢ ᴩᴏʟʟɪɴɢ...")
        app_bot.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
