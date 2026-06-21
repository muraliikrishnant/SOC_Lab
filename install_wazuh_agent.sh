#!/bin/bash

# Wazuh Agent Installation Script for Raspberry Pi Kali Linux
# Run this on your Raspberry Pi as root or with sudo

echo "=================================="
echo "Wazuh Agent Setup for Kali Linux"
echo "=================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use: sudo ./install_wazuh_agent.sh)"
   exit 1
fi

# Get macbook IP from user if not provided
if [ -z "$1" ]; then
    echo ""
    read -p "Enter your macbook IP address: " MACBOOK_IP
else
    MACBOOK_IP=$1
fi

echo ""
echo "Installing Wazuh Agent for Kali Linux..."
echo "Manager IP: $MACBOOK_IP"
echo ""

# Add Wazuh repository
echo "[*] Adding Wazuh repository..."
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list

# Update and install
echo "[*] Updating packages..."
apt-get update -y

echo "[*] Installing Wazuh Agent..."
apt-get install -y wazuh-agent

# Configure agent
echo "[*] Configuring Wazuh Agent..."

# Backup original config
cp /var/ossec/etc/ossec.conf /var/ossec/etc/ossec.conf.bak

# Replace manager IP in config
sed -i "s/<server ip=\".*\">/<server ip=\"$MACBOOK_IP\">/g" /var/ossec/etc/ossec.conf

# Ensure proper monitoring is configured
cat >> /var/ossec/etc/ossec.conf.new << 'EOF'
<localfile>
    <location>/var/log/auth.log</location>
    <log_format>syslog</log_format>
</localfile>

<localfile>
    <location>/var/log/syslog</location>
    <log_format>syslog</log_format>
</localfile>

<localfile>
    <location>/var/log/apt/history.log</location>
    <log_format>syslog</log_format>
</localfile>

<localfile>
    <location>/var/log/sudo.log</location>
    <log_format>syslog</log_format>
</localfile>
EOF

# Start and enable agent
echo "[*] Starting Wazuh Agent..."
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl start wazuh-agent

# Verify
echo ""
echo "=================================="
echo "Verification"
echo "=================================="
sleep 2

if systemctl is-active --quiet wazuh-agent; then
    echo "✅ Wazuh Agent is running"
else
    echo "❌ Wazuh Agent failed to start"
    systemctl status wazuh-agent
fi

echo ""
echo "Agent Configuration:"
grep -A 3 "<client>" /var/ossec/etc/ossec.conf

echo ""
echo "=================================="
echo "Next Steps"
echo "=================================="
echo "1. In Wazuh Dashboard (https://localhost:443):"
echo "   - Go to Agents section"
echo "   - Look for your Raspberry Pi hostname"
echo "   - Status should change to 'Active' within 2 minutes"
echo ""
echo "2. To monitor logs in real-time:"
echo "   sudo tail -f /var/ossec/logs/ossec.log"
echo ""
echo "3. To generate test events:"
echo "   for i in {1..10}; do ssh baduser@localhost 2>/dev/null; done"
echo ""
