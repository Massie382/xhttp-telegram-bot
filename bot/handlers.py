from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .db import (
    user_exists, create_user, get_user_lang, set_user_lang,
    set_linked_username, get_linked_username, unlink_user, is_linked,
    get_all_servers, get_server_by_name
)
from .strings import get_text
from .utils import unicode_bar, days_left_from_iso, format_bytes
from .api_client import XHTTPManagerClient
import re

WAITING_FOR_USERNAME = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_exists(user_id):
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="first_lang_en"),
             InlineKeyboardButton("🇮🇷 فارسی", callback_data="first_lang_fa")]
        ]
        await update.message.reply_text(
            "🌍 Welcome! Please select your language:\n———————————————\nبه بات XHTTP خوش آمدید!\n\nلطفاً زبان خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    lang = get_user_lang(user_id)
    await update.message.reply_text(get_text("welcome", lang))

async def first_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = "en" if query.data == "first_lang_en" else "fa"
    create_user(user_id, lang)
    if lang == "en":
        await query.edit_message_text("✅ Language set to English!\n\nSend /link to connect your account")
    else:
        await query.edit_message_text("✅ زبان به فارسی تنظیم شد!\n\nبرای اتصال حساب از /link استفاده کنید")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_user_lang(user_id)
    keyboard = [[
        InlineKeyboardButton("🇬🇧 English" + (" ✓" if current == "en" else ""), callback_data="lang_en"),
        InlineKeyboardButton("🇮🇷 فارسی" + (" ✓" if current == "fa" else ""), callback_data="lang_fa")
    ]]
    await update.message.reply_text("Select language:", reply_markup=InlineKeyboardMarkup(keyboard))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "en" if query.data == "lang_en" else "fa"
    set_user_lang(query.from_user.id, lang)
    if lang == "en":
        await query.edit_message_text("✅ Language set to English!")
    else:
        await query.edit_message_text("✅ زبان به فارسی تنظیم شد!")

async def link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if is_linked(user_id):
        keyboard = [[
            InlineKeyboardButton("✅ Yes", callback_data="link_overwrite"),
            InlineKeyboardButton("❌ No", callback_data="link_cancel")
        ]]
        await update.message.reply_text(
            f"Already linked to `{get_linked_username(user_id)}`. Overwrite?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_FOR_USERNAME
    await update.message.reply_text("📝 Send your XHTTP username:\n\nType /cancel to abort")
    return WAITING_FOR_USERNAME

async def link_overwrite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "link_overwrite":
        await query.edit_message_text("Send your new username:")
        return WAITING_FOR_USERNAME
    await query.edit_message_text("Cancelled")
    return ConversationHandler.END

async def link_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = update.message.text.strip()
    if len(username) < 3 or not re.match(r'^[a-zA-Z0-9_-]+$', username):
        await update.message.reply_text("❌ Invalid username. Try again or /cancel")
        return WAITING_FOR_USERNAME
    set_linked_username(user_id, username)
    await update.message.reply_text(f"✅ Linked to `{username}`!\n\nUse /status to check usage", parse_mode="Markdown")
    return ConversationHandler.END

async def link_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END

async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if not is_linked(user_id):
        await update.message.reply_text(get_text("not_linked", lang))
        return
    unlink_user(user_id)
    await update.message.reply_text(get_text("unlink_success", lang))

async def servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    servers = get_all_servers()
    if not servers:
        await update.message.reply_text(get_text("no_servers", lang))
        return
    names = "\n".join(f"• {s['name']}" for s in servers)
    await update.message.reply_text(get_text("servers_list", lang, names))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = get_linked_username(user_id)
    if not username:
        await update.message.reply_text(get_text("not_linked", lang))
        return

    servers = get_all_servers()
    if not servers:
        await update.message.reply_text(get_text("no_servers", lang))
        return

    await update.message.reply_text(get_text("fetching", lang))

    for server in servers:
        client = XHTTPManagerClient(server["base_url"], server["admin_token"])
        stats = await client.get_user_stats(username)
        
        if stats and "error" not in stats:
            used = stats.get("bytes_used", 0)
            cap = stats.get("data_cap_bytes", 0)
            status = stats.get("status", "unknown")
            max_dev = stats.get("max_devices", "Unlimited")
            
            used_str = format_bytes(used)
            cap_str = format_bytes(cap) if cap > 0 else "Unlimited"
            
            if cap and cap > 0:
                percent = (used / cap) * 100
                bar = unicode_bar(used, cap)
                message = (
                    f"📊 **{server['name']}**\n"
                    f"Status: {status}\n"
                    f"Used: {used_str}\n"
                    f"Limit: {cap_str}\n"
                    f"Progress: {bar} {percent:.1f}%\n"
                    f"Devices: {max_dev}"
                )
            else:
                message = (
                    f"📊 **{server['name']}**\n"
                    f"Status: {status}\n"
                    f"Used: {used_str}\n"
                    f"Limit: Unlimited\n"
                    f"Devices: {max_dev}"
                )
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ **{server['name']}**: No account found", parse_mode="Markdown")
        
        await client.close()

async def getconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = get_linked_username(user_id)
    if not username:
        await update.message.reply_text(get_text("not_linked", lang))
        return

    servers = get_all_servers()
    if not servers:
        await update.message.reply_text(get_text("no_servers", lang))
        return

    if context.args:
        target = context.args[0]
        for server in servers:
            if server["name"] == target:
                client = XHTTPManagerClient(server["base_url"], server["admin_token"])
                config = await client.get_user_config(username)
                if config:
                    await update.message.reply_text(
                        f"🔐 **{server['name']}**\n`{config}`",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(f"❌ **{server['name']}**: {get_text('no_account', lang)}")
                await client.close()
                return
        await update.message.reply_text(f"❌ Server '{target}' not found")
        return
    
    keyboard = []
    for server in servers:
        keyboard.append([InlineKeyboardButton(f"📡 {server['name']}", callback_data=f"getconfig_{server['name']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔐 **Select a server to get your VLESS config:**",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def getconfig_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    username = get_linked_username(user_id)
    
    if not username:
        await query.edit_message_text(get_text("not_linked", lang))
        return
    
    server_name = query.data.replace("getconfig_", "")
    server = get_server_by_name(server_name)
    
    if not server:
        await query.edit_message_text(f"❌ Server '{server_name}' not found")
        return
    
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    config = await client.get_user_config(username)
    
    if config:
        await query.edit_message_text(
            f"🔐 **{server['name']}**\n`{config}`",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(f"❌ **{server['name']}**: {get_text('no_account', lang)}")
    
    await client.close()

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = get_linked_username(user_id)
    
    if not username:
        await update.message.reply_text(get_text("not_linked", lang))
        return

    servers = get_all_servers()
    if not servers:
        await update.message.reply_text(get_text("no_servers", lang))
        return
    
    keyboard = []
    for server in servers:
        keyboard.append([InlineKeyboardButton(f"📱 {server['name']}", callback_data=f"qr_{server['name']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if lang == "en":
        await update.message.reply_text(
            "🎯 **Select a server to get the QR code:**\n\n"
            "Tap a button below to receive the QR code for your VLESS config.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🎯 **سرور مورد نظر را برای دریافت کد QR انتخاب کنید:**\n\n"
            "برای دریافت کد QR کانفیگ VLESS خود، روی دکمه زیر ضربه بزنید.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def qr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    username = get_linked_username(user_id)
    
    if not username:
        await query.edit_message_text(get_text("not_linked", lang))
        return
    
    server_name = query.data.replace("qr_", "")
    server = get_server_by_name(server_name)
    
    if not server:
        await query.edit_message_text(f"❌ Server '{server_name}' not found")
        return
    
    if lang == "en":
        await query.edit_message_text(f"⏳ Generating QR code for {server['name']}...")
    else:
        await query.edit_message_text(f"⏳ در حال تولید کد QR برای سرور {server['name']}...")
    
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    qr_bytes = await client.get_user_qr(username)
    await client.close()
    
    if qr_bytes:
        caption = get_text("qr_caption", lang, username, server_name)
        await query.delete_message()
        await context.bot.send_photo(chat_id=user_id, photo=qr_bytes, caption=caption)
    else:
        await query.edit_message_text(get_text("no_account", lang))
