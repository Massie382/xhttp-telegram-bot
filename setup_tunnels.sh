#!/usr/bin/env bash
# setup_tunnels.sh – Configure SSH tunnels to remote xhttp-manager APIs
# Run after installing the bot, or manually.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}XHTTP Telegram Bot – SSH Tunnel Setup${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Install autossh if not present
if ! command -v autossh &>/dev/null; then
    echo -e "${CYAN}Installing autossh...${NC}"
    apt-get update -qq
    apt-get install -y -qq autossh
fi

TUNNEL_CONFIG="/etc/xhttp-telegram-bot/tunnels.conf"
TUNNEL_SCRIPT="/usr/local/bin/xhttp-tunnels.sh"
SERVICE_FILE="/etc/systemd/system/xhttp-tunnels.service"

# Create tunnels.conf if it doesn't exist
if [[ ! -f "$TUNNEL_CONFIG" ]]; then
    cat > "$TUNNEL_CONFIG" <<'EOF'
# Format: remote_host local_port ssh_user
# Example:
# vpn1.example.com 7171 root
# vpn2.example.com 7172 root
EOF
    echo -e "${YELLOW}Created $TUNNEL_CONFIG – please edit it with your server details.${NC}"
fi

# Create the tunnel management script
cat > "$TUNNEL_SCRIPT" <<'EOF'
#!/bin/bash
# xhttp-tunnels.sh – Maintains SSH tunnels to remote xhttp-manager APIs
CONFIG="/etc/xhttp-telegram-bot/tunnels.conf"
if [[ ! -f "$CONFIG" ]]; then
    echo "No tunnel config found at $CONFIG"
    exit 1
fi

# Kill any existing autossh processes for our ports
pkill -f "autossh.*-L.*:717" 2>/dev/null || true
sleep 1

while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue
    read -r host port user <<< "$line"
    if [[ -n "$host" && -n "$port" && -n "$user" ]]; then
        echo "Starting tunnel: $host -> localhost:$port"
        autossh -M 0 -N -f -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" \
            -o "ExitOnForwardFailure=yes" \
            -L "${port}:127.0.0.1:7171" "${user}@${host}"
    fi
done < "$CONFIG"
EOF

chmod +x "$TUNNEL_SCRIPT"

# Create systemd service
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=XHTTP Manager SSH Tunnels
After=network.target

[Service]
Type=forking
ExecStart=$TUNNEL_SCRIPT
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo ""
echo -e "${GREEN}${BOLD}SSH tunnel support installed.${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Edit ${YELLOW}$TUNNEL_CONFIG${NC} and add your remote servers."
echo -e "     Format: ${CYAN}<remote_host> <local_port> <ssh_user>${NC}"
echo -e "     Example: ${CYAN}vpn1.example.com 7171 root${NC}"
echo -e "  2. Set up SSH key authentication from this server to each remote host:"
echo -e "     ${CYAN}ssh-keygen -t rsa${NC}"
echo -e "     ${CYAN}ssh-copy-id root@vpn1.example.com${NC}"
echo -e "  3. Start tunnels: ${CYAN}systemctl enable --now xhttp-tunnels${NC}"
echo -e "  4. In the bot, add servers with base_url ${CYAN}http://127.0.0.1:<local_port>${NC}"
echo ""