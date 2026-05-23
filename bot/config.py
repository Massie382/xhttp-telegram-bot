import os
import toml
from pathlib import Path

CONFIG_PATHS = [
    os.environ.get("XHTTP_TELEGRAM_CONFIG", ""),
    "/etc/xhttp-telegram-bot/config.toml",
    str(Path(__file__).parent.parent / "config.toml"),
]

_config = {}

for path in CONFIG_PATHS:
    if path and Path(path).exists():
        try:
            _config = toml.load(path)
            break
        except:
            pass

BOT_TOKEN = _config.get("bot", {}).get("token", "")
DB_PATH = _config.get("database", {}).get("path", "/var/lib/xhttp-telegram-bot/bot.db")