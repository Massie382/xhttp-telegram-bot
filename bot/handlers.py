from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .db import (
    user_exists, create_user, get_user_lang, set_user_lang,
    set_linked_username, get_linked_username, unlink_user, is_linked,
    get_all_servers, get_server_by_name
)
from .strings import get_text
from .utils import unicode_bar, format_bytes
from .api_client import XHTTPManagerClient
import re
import sqlite3

WAITING_FOR_USERNAME = 1

# Helper to read cumulative usage from the manager's DB
def get_cumulative_usage(username: str) -> int:
    db_path = "/var/lib/xhttp-manager/db.sqlite"
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT total_cumulative FROM cumulative_usage WHERE username = ?", (username.lower(),))
            row = cur.fetchone()
            return row[0] if row else 0
    except:
        return 0

# Helper to generate alternative configs with different hosts
def generate_alternative_configs(original_uri: str) -> dict:
    """
    Given a vless:// URI, replace the host part with two IP addresses.
    Returns a dict with keys 'original', 'ip1', 'ip2'.
    """
    if not original_uri.startswith('vless://'):
        return {'original': original_uri, 'ip1': original_uri, 'ip2': original_uri}
    parts = original_uri.split('@')
    if len(parts) != 2:
        return {'original': original_uri, 'ip1': original_uri, 'ip2': original_uri}
    uuid_part = parts[0]  # vless://uuid
    rest = parts[1]       # host:port?params#tag
    host_match = re.match(r'^([^:]+)(:.*)$', rest)
    if not host_match:
        return {'original': original_uri, 'ip1': original_uri, 'ip2': original_uri}
    original_host = host_match.group(1)
    suffix = host_match.group(2)
    ip1 = "198.169.2.1"
    ip2 = "1.98.169.2.65"
    uri_ip1 = f"{uuid_part}@{ip1}{suffix}"
    uri_ip2 = f"{uuid_part}@{ip2}{suffix}"
    return {
        'original': original_uri,
        'ip1': uri_ip1,
        'ip2': uri_ip2
    }

# -------------------- Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_exists(user_id):
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="first_lang_en"),
             InlineKeyboardButton("🇮🇷 فارسی", callback_data="first_lang_fa")]
        ]
        await update.message.reply_text(
            get_text("language_prompt", "en"),
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
    await query.edit_message_text(get_text("language_set", lang))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_user_lang(user_id)
    keyboard = [[
        InlineKeyboardButton("🇬🇧 English" + (" ✓" if current == "en" else ""), callback_data="lang_en"),
        InlineKeyboardButton("🇮🇷 فارسی" + (" ✓" if current == "fa" else ""), callback_data="lang_fa")
    ]]
    await update.message.reply_text(
        get_text("select_language", current),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "en" if query.data == "lang_en" else "fa"
    set_user_lang(query.from_user.id, lang)
    await query.edit_message_text(get_text("language_changed", lang))

async def link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if is_linked(user_id):
        keyboard = [[
            InlineKeyboardButton("✅ Yes", callback_data="link_overwrite"),
            InlineKeyboardButton("❌ No", callback_data="link_cancel")
        ]]
        await update.message.reply_text(
            get_text("already_linked", lang, get_linked_username(user_id)),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_FOR_USERNAME
    await update.message.reply_text(get_text("ask_username", lang))
    return WAITING_FOR_USERNAME

async def link_overwrite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    if query.data == "link_overwrite":
        await query.edit_message_text(get_text("ask_username_overwrite", lang))
        return WAITING_FOR_USERNAME
    await query.edit_message_text(get_text("cancelled", lang))
    return ConversationHandler.END

async def link_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    raw_username = update.message.text.strip()
    username_lower = raw_username.lower()

    if len(username_lower) < 3 or len(username_lower) > 64:
        await update.message.reply_text(get_text("invalid_length", lang))
        return WAITING_FOR_USERNAME
    if not re.match(r'^[a-zA-Z0-9_-]+$', username_lower):
        await update.message.reply_text(get_text("invalid_chars", lang))
        return WAITING_FOR_USERNAME

    checking_msg = await update.message.reply_text(get_text("checking_username", lang))
    servers = get_all_servers()
    if not servers:
        await checking_msg.edit_text(get_text("no_servers", lang))
        return ConversationHandler.END

    user_exists_on_server = False
    found_server = None
    for server in servers:
        client = XHTTPManagerClient(server["base_url"], server["admin_token"])
        users_list = await client.list_users(limit=1000)
        if users_list and 'users' in users_list:
            for u in users_list['users']:
                if u['username'].lower() == username_lower:
                    user_exists_on_server = True
                    found_server = server["name"]
                    break
        await client.close()
        if user_exists_on_server:
            break

    if not user_exists_on_server:
        await checking_msg.edit_text(get_text("user_not_found", lang, raw_username))
        return ConversationHandler.END

    set_linked_username(user_id, username_lower)
    await checking_msg.edit_text(get_text("link_success_with_server", lang, username_lower, found_server))
    return ConversationHandler.END

async def link_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    await update.message.reply_text(get_text("cancelled", lang))
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

# ------------------------------------------------------------
# STATUS COMMAND – uses cumulative usage from the new table
# ------------------------------------------------------------
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
        user_details = await client.get_user_details(username)
        if user_details and "error" not in user_details:
            cumulative = get_cumulative_usage(username)
            cap = user_details.get("data_cap_bytes", 0)
            status = user_details.get("status", "unknown")
            max_dev = user_details.get("max_devices", "Unlimited")

            used_str = format_bytes(cumulative)
            cap_str = format_bytes(cap) if cap > 0 else "Unlimited"

            if cap and cap > 0:
                percent = (cumulative / cap) * 100
                bar = unicode_bar(cumulative, cap)
                if lang == "en":
                    message = (
                        f"📊 **{server['name']}**\n"
                        f"Status: {status}\n"
                        f"Total Used (cumulative): {used_str}\n"
                        f"Limit: {cap_str}\n"
                        f"Progress: {bar} {percent:.1f}%\n"
                        f"Devices: {max_dev}"
                    )
                else:
                    message = (
                        f"📊 **{server['name']}**\n"
                        f"وضعیت: {status}\n"
                        f"مصرف کل (انباشته): {used_str}\n"
                        f"محدودیت: {cap_str}\n"
                        f"پیشرفت: {bar} {percent:.1f}%\n"
                        f"دستگاه‌ها: {max_dev}"
                    )
            else:
                if lang == "en":
                    message = (
                        f"📊 **{server['name']}**\n"
                        f"Status: {status}\n"
                        f"Total Used (cumulative): {used_str}\n"
                        f"Limit: Unlimited\n"
                        f"Devices: {max_dev}"
                    )
                else:
                    message = (
                        f"📊 **{server['name']}**\n"
                        f"وضعیت: {status}\n"
                        f"مصرف کل (انباشته): {used_str}\n"
                        f"محدودیت: نامحدود\n"
                        f"دستگاه‌ها: {max_dev}"
                    )
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ **{server['name']}**: {get_text('no_account', lang)}", parse_mode="Markdown")
        await client.close()

# ------------------------------------------------------------
# GETCONFIG – returns three configs (original + two IP versions)
# ------------------------------------------------------------
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
                    alts = generate_alternative_configs(config)
                    msg = (
                        f"🔐 **{server['name']}** – VLESS Configs:\n\n"
                        f"🌐 Original (domain):\n`{alts['original']}`\n\n"
                        f"📡 IP 1 (198.169.2.1):\n`{alts['ip1']}`\n\n"
                        f"📡 IP 2 (1.98.169.2.65):\n`{alts['ip2']}`"
                    )
                    await update.message.reply_text(msg, parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"❌ **{server['name']}**: {get_text('no_account', lang)}")
                await client.close()
                return
        await update.message.reply_text(get_text("server_not_found", lang, target))
        return

    keyboard = []
    for server in servers:
        keyboard.append([InlineKeyboardButton(f"📡 {server['name']}", callback_data=f"getconfig_{server['name']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text("select_server_config", lang),
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
        await query.edit_message_text(get_text("server_not_found", lang, server_name))
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    config = await client.get_user_config(username)
    if config:
        alts = generate_alternative_configs(config)
        msg = (
            f"🔐 **{server['name']}** – VLESS Configs:\n\n"
            f"🌐 Original (domain):\n`{alts['original']}`\n\n"
            f"📡 IP 1 (198.169.2.1):\n`{alts['ip1']}`\n\n"
            f"📡 IP 2 (1.98.169.2.65):\n`{alts['ip2']}`"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await query.edit_message_text(f"❌ **{server['name']}**: {get_text('no_account', lang)}")
    await client.close()

# ------------------------------------------------------------
# QR command – unchanged (only original config is used for QR)
# ------------------------------------------------------------
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
    await update.message.reply_text(
        get_text("select_server_qr", lang),
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
        await query.edit_message_text(get_text("server_not_found", lang, server_name))
        return
    await query.edit_message_text(get_text("generating_qr", lang, server['name']))
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    qr_bytes = await client.get_user_qr(username)
    await client.close()
    if qr_bytes:
        caption = get_text("qr_caption", lang, username, server_name)
        await query.delete_message()
        await context.bot.send_photo(chat_id=user_id, photo=qr_bytes, caption=caption)
    else:
        await query.edit_message_text(get_text("no_account", lang))
