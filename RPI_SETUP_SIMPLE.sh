#!/bin/bash

# Simple Wazuh Agent Setup for Raspberry Pi
# Usage: sudo bash RPI_SETUP_SIMPLE.sh

MACBOOK_IP="192.168.0.197"  # UPDATE THIS with your macbook IP

echo "================================"
echo "Wazuh Agent Setup for Kali Linux"
echo "================================"
echo ""
echo "Configuring to connect to: $MACBOOK_IP"
echo ""

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Add Wazuh repo
echo "[1/5] Adding Wazuh repository..."
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list

# Update packages
echo "[2/5] Updating packages..."
apt-get update -y

# Install Wazuh Agent
echo "[3/5] Installing Wazuh Agent..."
apt-get install -y wazuh-agent

# Configure agent
echo "[4/5] Configuring agent..."
cp /var/ossec/etc/ossec.conf /var/ossec/etc/ossec.conf.bak
sed -i "s/<server ip=\".*\">/<server ip=\"$MACBOOK_IP\">/g" /var/ossec/etc/ossec.conf

# Start agent
echo "[5/5] Starting agent..."
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl restart wazuh-agent

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "Agent status:"
systemctl status wazuh-agent --no-pager

echo ""
echo "Configuration:"
grep -A 3 "<client>" /var/ossec/etc/ossec.conf

echo ""
echo "View live logs:"
echo "  sudo tail -f /var/ossec/logs/ossec.log"
echo ""
echo "Expected output:"
echo "  INFO: Agent connected successfully"
echo ""
