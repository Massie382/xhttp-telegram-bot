from telegram import Update
from telegram.ext import ContextTypes
from .db import (
    get_user_lang, is_admin, add_server, remove_server, get_server_by_name,
    get_all_servers, set_admin, get_all_linked_users, get_linked_username
)
from .strings import get_text
from .api_client import XHTTPManagerClient

async def _admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            lang = get_user_lang(user_id)
            await update.message.reply_text(get_text("admin_denied", lang))
            return
        return await func(update, context)
    return wrapper

@_admin_only
async def addserver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /addserver <name> <base_url> <admin_token>")
        return
    name, base_url, token = args
    client = XHTTPManagerClient(base_url, token)
    if not await client.health():
        await update.message.reply_text("❌ Cannot connect to API. Check URL and token.")
        return
    if add_server(name, base_url, token):
        set_admin(user_id, True)
        await update.message.reply_text(get_text("admin_promoted", lang, name))
    else:
        await update.message.reply_text("❌ Server name already exists.")

@_admin_only
async def removeserver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removeserver <name>")
        return
    name = context.args[0]
    if remove_server(name):
        await update.message.reply_text(f"✅ Server '{name}' removed.")
    else:
        await update.message.reply_text(f"❌ Server '{name}' not found.")

@_admin_only
async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /adduser <server> <username> [expiry_days] [data_cap_gb] [max_devices]")
        return
    server_name, username = args[0], args[1]
    expiry_days = int(args[2]) if len(args) > 2 else None
    data_cap_gb = float(args[3]) if len(args) > 3 else None
    max_devices = int(args[4]) if len(args) > 4 else None
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    result = await client.create_user(username, expiry_days, data_cap_gb, max_devices)
    if "username" in result:
        vless_uri = result.get("vless_uri", "")
        await update.message.reply_text(
            f"✅ User '{username}' created on {server_name}\n\n🔐 Config:\n`{vless_uri}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Failed: {result}")

@_admin_only
async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /removeuser <server> <username>")
        return
    server_name, username = context.args
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    result = await client.revoke_user(username)
    await update.message.reply_text(f"✅ User '{username}' revoked on {server_name}.")

@_admin_only
async def suspend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /suspend <server> <username>")
        return
    server_name, username = context.args
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    await client.suspend_user(username)
    await update.message.reply_text(f"⏸️ User '{username}' suspended on {server_name}.")

@_admin_only
async def unsuspend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /unsuspend <server> <username>")
        return
    server_name, username = context.args
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    await client.unsuspend_user(username)
    await update.message.reply_text(f"✅ User '{username}' unsuspended on {server_name}.")

@_admin_only
async def extend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /extend <server> <username> <days>")
        return
    server_name, username, days = context.args
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    await client.extend_user(username, int(days))
    await update.message.reply_text(f"✅ User '{username}' extended by {days} days on {server_name}.")

@_admin_only
async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /listusers <server> [status]")
        return
    server_name = context.args[0]
    status = context.args[1] if len(context.args) > 1 else "active"
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    data = await client.list_users(status)
    if data and "users" in data:
        users = data["users"]
        if not users:
            await update.message.reply_text("No users found.")
            return
        lines = [f"👥 Users on {server_name} (status: {status}):"]
        for u in users[:20]:
            lines.append(f"• {u['username']} - expiry: {u.get('expiry_at', 'none')[:10]}")
        await update.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text("Failed to fetch users.")

@_admin_only
async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /userinfo <server> <username>")
        return
    server_name, username = context.args
    server = get_server_by_name(server_name)
    if not server:
        await update.message.reply_text(f"❌ Server '{server_name}' not found.")
        return
    client = XHTTPManagerClient(server["base_url"], server["admin_token"])
    details = await client.get_user_details(username)
    if details:
        msg = f"User: {username}\nUUID: {details.get('uuid')}\nStatus: {details.get('status')}\nExpiry: {details.get('expiry_at')}\nData cap: {details.get('data_cap_bytes')}\nUsed: {details.get('bytes_used')}\nDevices: {details.get('max_devices')}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("User not found.")

@_admin_only
async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /lookup <username>")
        return
    username = context.args[0]
    servers = get_all_servers()
    if not servers:
        await update.message.reply_text("No servers configured.")
        return
    lines = [f"🔍 Lookup for `{username}`:"]
    for server in servers:
        client = XHTTPManagerClient(server["base_url"], server["admin_token"])
        stats = await client.get_user_stats(username)
        if stats and "error" not in stats:
            lines.append(f"• {server['name']}: {stats.get('status', 'unknown')} - {stats.get('total', 0)} bytes")
        else:
            lines.append(f"• {server['name']}: No account")
        await client.close()
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@_admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    users = get_all_linked_users()
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 {message}")
            count += 1
        except:
            pass
    await update.message.reply_text(f"📢 Broadcast sent to {count} users.")