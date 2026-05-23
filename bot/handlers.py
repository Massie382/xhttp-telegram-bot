from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from .db import (
    user_exists, create_user, get_user_lang, set_user_lang, 
    set_linked_username, get_linked_username, unlink_user, is_linked,
    get_all_servers
)
from .strings import get_text
from .utils import unicode_bar, days_left_from_iso, format_bytes
from .api_client import XHTTPManagerClient
import re

# Conversation states
WAITING_FOR_USERNAME = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - force language selection for new users."""
    user_id = update.effective_user.id
    
    # Check if user exists in database
    if not user_exists(user_id):
        # New user - ask for language first
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="first_lang_en"),
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="first_lang_fa"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌍 Welcome to XHTTP Bot!\n\n"
            "Please select your language:\n"
            "———————————————\n"
            "به بات XHTTP خوش آمدید!\n\n"
            "لطفاً زبان خود را انتخاب کنید:",
            reply_markup=reply_markup
        )
        return
    
    # Existing user - show normal welcome
    lang = get_user_lang(user_id)
    await update.message.reply_text(get_text("welcome", lang))

async def first_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle first-time language selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = "en" if query.data == "first_lang_en" else "fa"
    
    # Save user with selected language
    create_user(user_id, lang)
    
    # Send welcome message in selected language
    if lang == "en":
        await query.edit_message_text(
            "✅ Language set to English!\n\n"
            "👋 Welcome to XHTTP Bot!\n\n"
            "To get started, use /link to connect your XHTTP account.\n\n"
            "Commands:\n"
            "• /link - Connect your XHTTP username\n"
            "• /status - Check your usage\n"
            "• /getconfig - Get your VLESS config\n"
            "• /qr - Get QR code\n"
            "• /language - Change language"
        )
    else:
        await query.edit_message_text(
            "✅ زبان به فارسی تنظیم شد!\n\n"
            "👋 به بات XHTTP خوش آمدید!\n\n"
            "برای شروع، از /link برای اتصال حساب XHTTP خود استفاده کنید.\n\n"
            "دستورات:\n"
            "• /link - اتصال حساب XHTTP\n"
            "• /status - مشاهده وضعیت مصرف\n"
            "• /getconfig - دریافت کانفیگ VLESS\n"
            "• /qr - دریافت کد QR\n"
            "• /language - تغییر زبان"
        )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow user to change language after initial setup."""
    user_id = update.effective_user.id
    current_lang = get_user_lang(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English" + (" ✓" if current_lang == "en" else ""), callback_data="lang_en"),
            InlineKeyboardButton("🇮🇷 فارسی" + (" ✓" if current_lang == "fa" else ""), callback_data="lang_fa"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select your language / زبان خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language change after initial setup."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = "en" if query.data == "lang_en" else "fa"
    set_user_lang(user_id, lang)
    
    if lang == "en":
        await query.edit_message_text("✅ Language set to English!")
    else:
        await query.edit_message_text("✅ زبان به فارسی تنظیم شد!")

async def link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the link conversation - ask for username."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    # Check if already linked
    if is_linked(user_id):
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, overwrite", callback_data="link_overwrite"),
                InlineKeyboardButton("❌ No, cancel", callback_data="link_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⚠️ You are already linked to `{get_linked_username(user_id)}`.\n\nDo you want to overwrite?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return WAITING_FOR_USERNAME
    
    # Not linked yet, ask for username
    await update.message.reply_text(
        "📝 Please send your XHTTP username.\n\n"
        "You can type it directly in this chat.\n"
        "Example: `john_doe`\n\n"
        "Type /cancel to abort.",
        parse_mode="Markdown"
    )
    return WAITING_FOR_USERNAME

async def link_overwrite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle overwrite confirmation."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "link_overwrite":
        await query.edit_message_text(
            "📝 Please send your new XHTTP username.\n\n"
            "Type /cancel to abort."
        )
        return WAITING_FOR_USERNAME
    else:
        await query.edit_message_text("✅ Link operation cancelled.")
        return ConversationHandler.END

async def link_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the username from user and save it."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = update.message.text.strip()
    
    # Basic validation
    if len(username) < 3 or len(username) > 64:
        await update.message.reply_text(
            "❌ Username must be between 3 and 64 characters.\n\n"
            "Please send a valid username or /cancel."
        )
        return WAITING_FOR_USERNAME
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        await update.message.reply_text(
            "❌ Username can only contain letters, numbers, underscores (_), and hyphens (-).\n\n"
            "Please send a valid username or /cancel."
        )
        return WAITING_FOR_USERNAME
    
    # Save the link
    set_linked_username(user_id, username)
    
    await update.message.reply_text(
        f"✅ Successfully linked to `{username}`!\n\n"
        f"Now you can use:\n"
        f"• /status - Check your usage\n"
        f"• /getconfig - Get your VLESS config\n"
        f"• /qr - Get QR code",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def link_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the link conversation."""
    await update.message.reply_text("✅ Link operation cancelled.")
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

    await update.message.reply_text("⏳ Fetching stats from all servers...")

    results = []
    for server in servers:
        client = XHTTPManagerClient(server["base_url"], server["admin_token"])
        stats = await client.get_user_stats(username)
        details = await client.get_user_details(username) if stats and "error" not in stats else None
        results.append((server["name"], stats, details))
        await client.close()

    lines = [get_text("usage_header", lang, username)]
    for name, stats, details in results:
        lines.append(f"🌍 **{name}**")
        if not stats or "error" in stats:
            lines.append(get_text("no_account", lang))
            lines.append("")
            continue

        status = stats.get("status", "unknown")
        if status == "active":
            status_text = get_text("status_active", lang)
        elif status == "suspended":
            status_text = get_text("status_suspended", lang)
        else:
            status_text = get_text("status_revoked", lang)
        lines.append(f"Status: {status_text}")

        total = stats.get("total", 0)
        cap = stats.get("data_cap_bytes", 0)
        if cap and cap > 0:
            used_gb = total / (1024**3)
            cap_gb = cap / (1024**3)
            percent = (total / cap) * 100
            bar = unicode_bar(total, cap)
            lines.append(get_text("data_label", lang, bar, used_gb, cap_gb, percent))
        else:
            lines.append(get_text("data_unlimited", lang))

        expiry_iso = details.get("expiry_at") if details else None
        days, expired = days_left_from_iso(expiry_iso)
        if expired:
            lines.append(get_text("days_expired", lang))
        elif days is not None:
            lines.append(get_text("days_left", lang, days))

        max_dev = stats.get("max_devices")
        if max_dev:
            lines.append(get_text("devices", lang, max_dev))

        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

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

    target_server = context.args[0] if context.args else None

    for server in servers:
        if target_server and server["name"] != target_server:
            continue
        client = XHTTPManagerClient(server["base_url"], server["admin_token"])
        config = await client.get_user_config(username)
        if config:
            msg = get_text("config_header", lang, server["name"]) + get_text("config_body", lang, config)
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {server['name']}: {get_text('no_account', lang)}")
        await client.close()
        if target_server:
            break

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if len(context.args) != 1:
        await update.message.reply_text(get_text("usage", lang).format("/qr <server_name>"))
        return
    server_name = context.args[0]
    username = get_linked_username(user_id)
    if not username:
        await update.message.reply_text(get_text("not_linked", lang))
        return
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(get_text("error", lang, f"Server '{server_name}' not found"))
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    qr_bytes = await client.get_user_qr(username)
    await client.close()
    if qr_bytes:
        caption = get_text("qr_caption", lang, username, server_name)
        await update.message.reply_photo(photo=qr_bytes, caption=caption)
    else:
        await update.message.reply_text(get_text("no_account", lang))
