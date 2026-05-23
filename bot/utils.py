import datetime
from typing import Optional, Tuple

def format_bytes(bytes_val: int) -> str:
    """Convert bytes to human readable format (B, KB, MB, GB)."""
    if bytes_val == 0:
        return "0 B"
    
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_val >= 1024 and i < len(sizes) - 1:
        bytes_val /= 1024.0
        i += 1
    
    if i <= 1:
        return f"{bytes_val:.0f} {sizes[i]}"
    else:
        return f"{bytes_val:.2f} {sizes[i]}"

def unicode_bar(used_bytes: int, cap_bytes: int, width: int = 20) -> str:
    """Return a Unicode progress bar with emoji indicator."""
    if cap_bytes == 0:
        return "∞"
    
    percent = used_bytes / cap_bytes
    filled = int(round(percent * width))
    empty = width - filled
    
    filled = max(0, min(filled, width))
    empty = width - filled
    
    bar = "█" * filled + "░" * empty
    
    if percent < 0.75:
        indicator = "🟢"
    elif percent < 0.90:
        indicator = "🟡"
    else:
        indicator = "🔴"
    
    return f"{indicator} `[{bar}]`"

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
