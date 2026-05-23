import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from .db import (
    get_user_lang, set_user_lang, get_linked_username, set_linked_username,
    unlink_user, is_linked, get_all_servers, get_server_by_name, add_server,
    set_admin, is_admin
)
from .strings import get_text
from .utils import unicode_bar, days_left_from_iso, format_bytes
from .api_client import XHTTPManagerClient

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    await update.message.reply_text(get_text("welcome", lang))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")]
    ]
    await update.message.reply_text("Select your language / انتخاب زبان:", reply_markup=InlineKeyboardMarkup(keyboard))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "en" if query.data == "lang_en" else "fa"
    set_user_lang(query.from_user.id, lang)
    await query.edit_message_text(get_text("language_changed", lang))

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if len(context.args) != 1:
        await update.message.reply_text(get_text("usage", lang).format("/link <username>"))
        return
    username = context.args[0]
    set_linked_username(user_id, username)
    await update.message.reply_text(get_text("link_success", lang, username))

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

        # Status
        status = stats.get("status", "unknown")
        if status == "active":
            status_text = get_text("status_active", lang)
        elif status == "suspended":
            status_text = get_text("status_suspended", lang)
        else:
            status_text = get_text("status_revoked", lang)
        lines.append(f"Status: {status_text}")

        # Data usage
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

        # Expiry
        expiry_iso = details.get("expiry_at") if details else None
        days, expired = days_left_from_iso(expiry_iso)
        if expired:
            lines.append(get_text("days_expired", lang))
        elif days is not None:
            lines.append(get_text("days_left", lang, days))
        else:
            lines.append(get_text("days_left", lang, "∞"))

        # Devices
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