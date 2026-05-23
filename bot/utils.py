import datetime
from typing import Optional, Tuple

def unicode_bar(used_bytes: int, cap_bytes: int, width: int = 20) -> str:
    """Return a Unicode progress bar with emoji indicator."""
    if cap_bytes == 0:
        return "∞"
    percent = used_bytes / cap_bytes
    filled = int(round(percent * width))
    empty = width - filled
    bar = "█" * filled + "░" * empty
    if percent < 0.75:
        indicator = "🟢"
    elif percent < 0.90:
        indicator = "🟡"
    else:
        indicator = "🔴"
    return f"{indicator} `[{bar}]`"

def format_bytes(bytes_val: int) -> str:
    """Return human readable bytes (GB)."""
    return f"{bytes_val / (1024**3):.1f} GB"

def days_left_from_iso(expiry_iso: Optional[str]) -> Tuple[Optional[int], bool]:
    """Return (days_left, expired). expiry_iso like '2025-12-31T23:59:59Z'."""
    if not expiry_iso:
        return None, False
    try:
        expiry = datetime.datetime.fromisoformat(expiry_iso.replace('Z', '+00:00'))
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = expiry - now
        days = delta.days
        return days, days < 0
    except:
        return None, False