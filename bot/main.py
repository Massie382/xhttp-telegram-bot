#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from bot.config import BOT_TOKEN
from bot.db import init_db
from bot.handlers import (
    start, first_language_callback,
    language_command, language_callback,
    link_start, link_receive_username, link_cancel, link_overwrite_callback,
    unlink_command, servers_command, status_command, 
    getconfig_command, getconfig_callback, qr_command, qr_callback
)
from bot.admin_handlers import (
    addserver_command, removeserver_command, adduser_command, removeuser_command,
    suspend_command, unsuspend_command, extend_command, listusers_command,
    userinfo_command, lookup_command, broadcast_command
)

WAITING_FOR_USERNAME = 1

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set in config.toml")
        sys.exit(1)

    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(first_language_callback, pattern="^first_lang_"))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    
    link_conv = ConversationHandler(
        entry_points=[CommandHandler("link", link_start)],
        states={
            WAITING_FOR_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, link_receive_username),
                CallbackQueryHandler(link_overwrite_callback, pattern="^link_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", link_cancel)],
    )
    app.add_handler(link_conv)
    
    app.add_handler(CommandHandler("unlink", unlink_command))
    app.add_handler(CommandHandler("servers", servers_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("getconfig", getconfig_command))
    app.add_handler(CommandHandler("qr", qr_command))
    
    app.add_handler(CallbackQueryHandler(getconfig_callback, pattern="^getconfig_"))
    app.add_handler(CallbackQueryHandler(qr_callback, pattern="^qr_"))

    app.add_handler(CommandHandler("addserver", addserver_command))
    app.add_handler(CommandHandler("removeserver", removeserver_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("suspend", suspend_command))
    app.add_handler(CommandHandler("unsuspend", unsuspend_command))
    app.add_handler(CommandHandler("extend", extend_command))
    app.add_handler(CommandHandler("listusers", listusers_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("lookup", lookup_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))

    async def post_init(application):
        await application.bot.set_my_commands([
            ("start", "Start the bot"),
            ("language", "Change language"),
            ("link", "Link your XHTTP account"),
            ("unlink", "Unlink your account"),
            ("status", "Check your usage"),
            ("servers", "List all servers"),
            ("getconfig", "Get VLESS config"),
            ("qr", "Get QR code"),
            ("addserver", "[Admin] Add a server"),
            ("adduser", "[Admin] Create user"),
            ("removeuser", "[Admin] Remove user"),
            ("suspend", "[Admin] Suspend user"),
            ("unsuspend", "[Admin] Unsuspend user"),
            ("extend", "[Admin] Extend expiry"),
            ("listusers", "[Admin] List users"),
            ("lookup", "[Admin] Lookup user"),
            ("broadcast", "[Admin] Broadcast message"),
        ])
        print("✅ Bot commands set")
    
    app.post_init = post_init

    print("✅ XHTTP Telegram Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
