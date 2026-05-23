#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from bot.config import BOT_TOKEN
from bot.db import init_db
from bot.handlers import (
    start, language_command, language_callback, link_command, unlink_command,
    servers_command, status_command, getconfig_command, qr_command
)
from bot.admin_handlers import (
    addserver_command, removeserver_command, adduser_command, removeuser_command,
    suspend_command, unsuspend_command, extend_command, listusers_command,
    userinfo_command, lookup_command, broadcast_command
)

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set in config.toml")
        sys.exit(1)

    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("unlink", unlink_command))
    app.add_handler(CommandHandler("servers", servers_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("getconfig", getconfig_command))
    app.add_handler(CommandHandler("qr", qr_command))

    # Admin commands
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

    print("✅ XHTTP Telegram Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()