# 🎉 SOC SIEM Lab - DEPLOYMENT COMPLETE!

## ✅ Status: ALL SERVICES RUNNING

| Service | Port | Status | URL |
|---------|------|--------|-----|
| Elasticsearch | 9200 | ✅ Healthy | http://localhost:9200 |
| Kibana | 5601 | ✅ Healthy | http://localhost:5601 |
| Ollama | 11434 | ✅ Running | http://localhost:11434 |

---

## 🔧 YOUR macbook IP ADDRESS

```
192.168.0.197
```

**⚠️ IMPORTANT: Save this IP! You'll use it to configure the Raspberry Pi Wazuh Agent.**

---

## 📋 NEXT STEPS - DO THIS NOW

### Step 1: Configure Raspberry Pi (10 minutes)

**On your Raspberry Pi Terminal:**

```bash
# SSH into Raspberry Pi from macbook
ssh kali@192.168.1.50

# Download the installer script (option A - copy from macbook)
# OR manually install with these commands:

# Add Wazuh repository
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list

# Install Wazuh Agent
sudo apt-get update -y
sudo apt-get install -y wazuh-agent

# Edit config file
sudo nano /var/ossec/etc/ossec.conf

# Find the line: <server ip="MANAGER_IP">
# REPLACE MANAGER_IP WITH: 192.168.0.197

# Example (line 41-45 should look like):
# <client>
#     <server ip="192.168.0.197">
#         <port>1514</port>
#         <protocol>tcp</protocol>
#     </server>

# Save the file: Ctrl+X, Y, Enter

# Add these monitoring rules to the config (before </ossec_config>):
sudo cat >> /var/ossec/etc/ossec.conf << 'EOF'

<localfile>
    <location>/var/log/auth.log</location>
    <log_format>syslog</log_format>
</localfile>

<localfile>
    <location>/var/log/syslog</location>
    <log_format>syslog</log_format>
</localfile>
EOF

# Restart the agent
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl restart wazuh-agent

# Verify it's running
sudo systemctl status wazuh-agent

# Watch logs to confirm connection
sudo tail -f /var/ossec/logs/ossec.log
```

**You should see: "Agent connected successfully"** ✅

---

### Step 2: Verify Agent in Kibana (2 minutes)

Open on macbook: **http://localhost:5601**

1. Click on "Discover" in left sidebar
2. You should see logs appearing from Raspberry Pi
3. Go to Management → Data Views
4. Create a new data view called "logs-*"
5. Time field: @timestamp

---

### Step 3: Generate Test Events (5 minutes)

**Back on Raspberry Pi Terminal:**

```bash
# Create suspicious activity that will show up in your Kibana dashboard

# Failed SSH attempts
for i in {1..10}; do
  ssh baduser@localhost 2>/dev/null &
done

# Scan network
nmap localhost

# Access system files
sudo cat /etc/shadow

# Install packages
sudo apt-get install -y htop

# View system info
sudo whoami
uname -a
```

**Check Kibana dashboard** - you should see these events appear in real-time!

---

### Step 4: Pull Ollama AI Model (5-10 minutes)

**On macbook Terminal:**

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM

# Pull the AI model (this is ~4GB - takes a few minutes)
docker compose exec ollama ollama pull mistral

# Verify it's loaded
docker compose exec ollama ollama list
```

---

### Step 5: Start Alert Analyzer (Optional - for Discord alerts)

**New Terminal on macbook:**

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM

# Optional: If you have a Discord webhook, set it first
export DISCORD_WEBHOOK="your_webhook_url_here"

# Run the analyzer
python3 alert_analyzer.py
```

This will:
- Monitor for new Elasticsearch logs every 30 seconds
- Use Ollama AI to analyze potential threats
- Send alerts to Discord (if webhook configured)
- Display analysis in terminal

---

## 📊 DASHBOARDS & URLS

| What | URL | Notes |
|------|-----|-------|
| **Kibana Logs** | http://localhost:5601 | Main dashboard - see Raspberry Pi logs |
| **Elasticsearch API** | http://localhost:9200 | Raw API access |
| **Ollama API** | http://localhost:11434 | AI threat analysis |

---

## 🔍 WHAT'S HAPPENING

```
Raspberry Pi 5 (Kali)
    ↓
Sends syslog to port 1514 on macbook (192.168.0.197)
    ↓
Elasticsearch receives & indexes the logs
    ↓
Kibana displays real-time dashboard
    ↓
Alert Analyzer watches for new events
    ↓
Ollama AI analyzes potential threats
    ↓
Discord webhook sends alerts (optional)
```

---

## 🛠 TROUBLESHOOTING

### Raspberry Pi Agent Not Connecting

```bash
# On Raspberry Pi - verify connectivity
ping 192.168.0.197
nc -zv 192.168.0.197 1514

# Check agent logs
sudo tail -f /var/ossec/logs/ossec.log

# Restart agent
sudo systemctl restart wazuh-agent
```

### No Logs in Kibana

1. Make sure Raspberry Pi agent is running: `sudo systemctl status wazuh-agent`
2. Check Elasticsearch has data: `curl http://localhost:9200/_cat/indices`
3. Reload Kibana page
4. Generate test events on Raspberry Pi

### Ollama Models Not Loading

```bash
docker compose exec ollama ollama pull mistral
docker compose logs ollama
```

### Want to Stop Services

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose down
```

### Want to Restart Services

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose up -d
```

---

## 📁 FILE STRUCTURE

```
/Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM/
├── docker-compose.yml           # Main Docker setup
├── alert_analyzer.py            # AI alert analyzer script
├── install_wazuh_agent.sh       # Raspberry Pi installer
├── QUICK_START.md              # Quick reference
├── DEPLOYMENT_INFO.md          # This file
├── SOC_SIEM_SETUP_GUIDE.md    # Detailed guide
└── SOC_SIEM_RPI_SETUP.md      # Raspberry Pi specifics
```

---

## 🎯 WHAT YOU'VE BUILT

A **real enterprise-grade SOC (Security Operations Center)** that:

✅ Collects logs from remote Kali Linux system (Raspberry Pi 5)
✅ Stores and indexes logs in Elasticsearch
✅ Visualizes logs in real-time Kibana dashboard
✅ Analyzes threats with AI (Ollama)
✅ Can send automated alerts to Discord

**Similar to:** The LinkedIn post you shared! 🚀

---

## 🚀 ADVANCED FEATURES (OPTIONAL)

Once you have the basics working:

1. **Create Kibana Visualizations** for specific threats
2. **Set up N8N or Shuffle** for automated response workflows
3. **Add more endpoints** (other VMs, laptops)
4. **Configure Discord webhooks** for team alerts
5. **Monitor 24/7** with saved dashboards

---

## ❓ QUESTIONS?

Refer to:
- `QUICK_START.md` - Quick reference
- `SOC_SIEM_RPI_SETUP.md` - Detailed Raspberry Pi setup
- `SOC_SIEM_SETUP_GUIDE.md` - Full architecture & explanation

---

## 🎉 You're Ready to Start!

**Your SOC Lab is fully deployed and waiting for logs.**

**Next action:** Configure your Raspberry Pi agent (see Step 1 above) ⬆️

**Enjoy your security lab! 🛡️**
