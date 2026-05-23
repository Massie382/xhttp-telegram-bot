#!/usr/bin/env bash
set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}  XHTTP Telegram Bot Installer${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check for Debian/Ubuntu
if ! command -v apt-get &>/dev/null; then
    echo -e "${RED}Error: This installer requires apt-get (Debian/Ubuntu).${NC}"
    exit 1
fi

# Determine script directory (supports curl | bash)
if [[ -z "${BASH_SOURCE[0]:-}" || ! -f "${BASH_SOURCE[0]}" ]]; then
    REPO_URL="https://raw.githubusercontent.com/yourusername/xhttp-telegram-bot/main"
    TMPDIR=$(mktemp -d /tmp/xhttp-telegram-bot.XXXXXX)
    cd "$TMPDIR"
    echo -e "${CYAN}Downloading installer files...${NC}"
    curl -fsSL -O "$REPO_URL/install.sh"
    curl -fsSL -O "$REPO_URL/requirements.txt"
    curl -fsSL -O "$REPO_URL/config.example.toml"
    curl -fsSL -O "$REPO_URL/setup_tunnels.sh"  # ✅ FIX: download tunnel script
    mkdir -p bot systemd
    curl -fsSL "$REPO_URL/bot/main.py" -o bot/main.py
    curl -fsSL "$REPO_URL/bot/config.py" -o bot/config.py
    curl -fsSL "$REPO_URL/bot/db.py" -o bot/db.py
    curl -fsSL "$REPO_URL/bot/api_client.py" -o bot/api_client.py
    curl -fsSL "$REPO_URL/bot/handlers.py" -o bot/handlers.py
    curl -fsSL "$REPO_URL/bot/admin_handlers.py" -o bot/admin_handlers.py
    curl -fsSL "$REPO_URL/bot/utils.py" -o bot/utils.py
    curl -fsSL "$REPO_URL/bot/strings.py" -o bot/strings.py
    curl -fsSL "$REPO_URL/systemd/xhttp-telegram-bot.service" -o systemd/xhttp-telegram-bot.service
    exec bash install.sh
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/xhttp-telegram-bot"
CONFIG_DIR="/etc/xhttp-telegram-bot"
DATA_DIR="/var/lib/xhttp-telegram-bot"

echo -e "${CYAN}[1/5] Installing system packages...${NC}"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip jq curl sqlite3 rsync  # ✅ FIX: added rsync
echo -e "      ${GREEN}✔ Dependencies installed${NC}"

echo -e "${CYAN}[2/5] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR"
echo -e "      ${GREEN}✔ Directories created${NC}"

echo -e "${CYAN}[3/5] Copying bot files...${NC}"
rsync -a --delete "$SCRIPT_DIR/bot/" "$INSTALL_DIR/bot/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/"
if [[ -f "$SCRIPT_DIR/setup_tunnels.sh" ]]; then
    cp "$SCRIPT_DIR/setup_tunnels.sh" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/setup_tunnels.sh"
fi
chmod +x "$INSTALL_DIR/uninstall.sh"
echo -e "      ${GREEN}✔ Files copied${NC}"

echo -e "${CYAN}[4/5] Setting up Python virtual environment...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo -e "      ${GREEN}✔ Python environment ready${NC}"

echo -e "${CYAN}[5/5] Configuring bot...${NC}"
if [[ ! -f "$CONFIG_DIR/config.toml" ]]; then
    cp "$SCRIPT_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
    echo -e "      ${YELLOW}⚠ Please edit $CONFIG_DIR/config.toml and add your bot token${NC}"
fi

# Optional SSH tunnel setup
echo ""
echo -e "${CYAN}Do you want to set up SSH tunnels to remote xhttp-manager servers?${NC}"
read -p "This allows the bot to connect securely without opening firewall ports. (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -f "$INSTALL_DIR/setup_tunnels.sh" ]]; then
        bash "$INSTALL_DIR/setup_tunnels.sh"
    elif [[ -f "$SCRIPT_DIR/setup_tunnels.sh" ]]; then
        bash "$SCRIPT_DIR/setup_tunnels.sh"
    else
        echo -e "${RED}setup_tunnels.sh not found. Please download it manually from the repository.${NC}"
    fi
else
    echo -e "  ${YELLOW}Skipping tunnel setup. You can run setup_tunnels.sh later.${NC}"
fi

# Systemd service
cp "$SCRIPT_DIR/systemd/xhttp-telegram-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable xhttp-telegram-bot.service

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║     XHTTP Telegram Bot INSTALLED SUCCESSFULLY ✔        ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "    1. Edit ${YELLOW}$CONFIG_DIR/config.toml${NC} and add your bot token."
echo -e "    2. Start the bot: ${CYAN}systemctl start xhttp-telegram-bot${NC}"
echo -e "    3. View logs: ${CYAN}journalctl -u xhttp-telegram-bot -f${NC}"
echo ""
echo -e "  ${BOLD}Uninstall:${NC} ${YELLOW}$INSTALL_DIR/uninstall.sh${NC}"