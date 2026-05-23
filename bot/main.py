#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    Application
)
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

async def setup_commands(app: Application) -> None:
    """Set the bot's command menu (visible when user types /)."""
    commands = [
        ("start", "Welcome message / راهنما"),
        ("language", "Switch language / تغییر زبان"),
        ("link", "Link your XHTTP username / اتصال حساب"),
        ("unlink", "Unlink your account / قطع اتصال"),
        ("status", "Show your usage / وضعیت مصرف"),
        ("servers", "List all servers / لیست سرورها"),
        ("getconfig", "Get VLESS config / دریافت کانفیگ"),
        ("qr", "Get QR code for a server / دریافت کد QR"),
        # Admin commands (only visible to admins, but listed for all)
        ("addserver", "[Admin] Add a new server"),
        ("removeserver", "[Admin] Remove a server"),
        ("adduser", "[Admin] Create a new user"),
        ("removeuser", "[Admin] Revoke a user"),
        ("suspend", "[Admin] Suspend a user"),
        ("unsuspend", "[Admin] Unsuspend a user"),
        ("extend", "[Admin] Extend user expiry"),
        ("listusers", "[Admin] List users on a server"),
        ("userinfo", "[Admin] Show full user details"),
        ("lookup", "[Admin] Lookup any user across servers"),
        ("broadcast", "[Admin] Send message to all users"),
    ]
    await app.bot.set_my_commands(commands)
    print("✅ Bot command menu set")

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

    # Set up the command menu
    # We need to run the async setup within the application's event loop.
    # The easiest way is to use app.post_init.
    async def post_init(application: Application):
        await setup_commands(application)
    app.post_init = post_init

    print("✅ XHTTP Telegram Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
