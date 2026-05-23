# XHTTP Telegram Bot

A Telegram bot that integrates with [xhttp-manager](https://github.com/Massie382/xhttp-manager) to provide cross‑server user management, usage stats, and configuration retrieval.

## Features

- **Multi‑server**: Query any number of xhttp-manager instances.
- **User self‑service**: Link your XHTTP username, view usage (with Unicode bars), get VLESS configs and QR codes.
- **Admin CLI mirror**: Create, revoke, suspend, extend, list users – all from Telegram.
- **Auto admin promotion**: The first user who adds a server becomes admin.
- **Bilingual**: English / Persian (RTL supported).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Massie382/xhttp-telegram-bot/main/install.sh | sudo bash
