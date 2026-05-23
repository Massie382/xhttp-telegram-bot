#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}XHTTP Telegram Bot Uninstaller${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: must run as root${NC}"
    exit 1
fi

INSTALL_DIR="/opt/xhttp-telegram-bot"
CONFIG_DIR="/etc/xhttp-telegram-bot"
DATA_DIR="/var/lib/xhttp-telegram-bot"

# Stop and disable service
if systemctl is-active --quiet xhttp-telegram-bot.service 2>/dev/null; then
    systemctl stop xhttp-telegram-bot.service
    echo -e "  ${GREEN}OK${NC} Service stopped"
fi
systemctl disable xhttp-telegram-bot.service 2>/dev/null || true
rm -f /etc/systemd/system/xhttp-telegram-bot.service
systemctl daemon-reload

# Remove files
rm -rf "$INSTALL_DIR"
echo -e "  ${GREEN}OK${NC} Removed $INSTALL_DIR"

read -p "Remove configuration and database? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$CONFIG_DIR" "$DATA_DIR"
    echo -e "  ${GREEN}OK${NC} Removed $CONFIG_DIR and $DATA_DIR"
else
    echo -e "  ${YELLOW}Preserved $CONFIG_DIR and $DATA_DIR${NC}"
fi

echo ""
echo -e "${GREEN}${BOLD}Uninstall complete.${NC}"