# 🚀 SOC SIEM Lab - Quick Start Guide

## What's Ready

✅ **docker-compose.yml** - Complete Wazuh stack with Elasticsearch, Kibana, Ollama
✅ **deploy.sh** - One-click deployment script
✅ **install_wazuh_agent.sh** - Wazuh agent installer for Raspberry Pi
✅ **alert_analyzer.py** - AI-powered alert analyzer with Discord integration

---

## Step 1: Deploy Everything (5 minutes)

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
chmod +x deploy.sh
./deploy.sh
```

This will:
- Start all Docker containers (Wazuh, Elasticsearch, Kibana, Ollama)
- Show you your macbook IP
- Display access URLs

**Wait for services to be fully ready (they take 2-3 minutes)**

---

## Step 2: Configure Raspberry Pi Agent (10 minutes)

### On Raspberry Pi Terminal:

```bash
# Copy the script to your Raspberry Pi
scp install_wazuh_agent.sh kali@192.168.1.50:/home/kali/

# SSH into Raspberry Pi
ssh kali@192.168.1.50

# Make it executable and run
sudo bash install_wazuh_agent.sh 192.168.1.100
# Replace 192.168.1.100 with your macbook IP
```

**That's it!** The agent will:
- Install Wazuh agent
- Configure it to send logs to your macbook
- Start automatically
- Begin shipping logs in ~30 seconds

---

## Step 3: Verify Agent is Connected (3 minutes)

On macbook, open: **https://localhost:443**
- Username: `admin`
- Password: `admin`

Navigate to **Agents** section → You should see your Raspberry Pi showing as **Active** ✅

---

## Step 4: View Live Dashboard

Open: **http://localhost:5601**
- Username: `elastic`
- Password: `SecurePassword123!`

You'll see Kibana dashboard with live Raspberry Pi logs!

---

## Step 5: Pull AI Models (5 minutes)

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose exec ollama ollama pull mistral

# This downloads the AI model (might take a few minutes)
# You can verify with:
docker compose exec ollama ollama list
```

---

## Step 6: Start Alert Analyzer (Optional - for Discord alerts)

In a new terminal:

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM

# Optional: Set Discord webhook (if you have one)
export DISCORD_WEBHOOK="your_webhook_url"

# Run analyzer
python3 alert_analyzer.py
```

The analyzer will:
- Monitor for new alerts every 30 seconds
- Use AI (Ollama) to analyze threats
- Send formatted alerts to Discord (if webhook is set)
- Display analysis in terminal

---

## Step 7: Generate Test Events (Real-time Testing)

On Raspberry Pi:

```bash
# SSH brute force attempts
for i in {1..10}; do
  ssh invalid_user@localhost 2>/dev/null &
done

# Network scan
nmap localhost

# File access
sudo cat /etc/shadow

# Package install
sudo apt install -y curl

# System commands
sudo whoami
```

Watch in real-time:
- **Kibana Dashboard** - See alerts appear live
- **Alert Analyzer terminal** - See AI analysis
- **Discord** - Receive automated alerts (if configured)

---

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Wazuh Manager | https://localhost:443 | admin / admin |
| Kibana | http://localhost:5601 | elastic / SecurePassword123! |
| Elasticsearch | http://localhost:9200 | elastic / SecurePassword123! |
| Ollama API | http://localhost:11434 | (no auth needed) |

---

## Troubleshooting

### Agent won't connect to Wazuh
```bash
# On Raspberry Pi
sudo systemctl restart wazuh-agent
sudo journalctl -u wazuh-agent -n 50
```

### Services not starting
```bash
# Check logs
docker compose logs -f wazuh-manager
docker compose logs -f elasticsearch
```

### Network issue (Raspberry Pi can't reach macbook)
```bash
# On Raspberry Pi
ping 192.168.1.100  # Replace with your macbook IP
nc -zv 192.168.1.100 1514
```

### Ollama models not loading
```bash
docker compose exec ollama ollama pull mistral
docker compose exec ollama ollama list
```

---

## Stopping Everything

```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose down
```

## Restarting Everything

```bash
./deploy.sh
```

---

## What You've Built

```
┌─────────────────────┐
│   Raspberry Pi 5    │
│   (Kali Linux)      │
│   Wazuh Agent       │ ─── Logs over network
└─────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│         macbook (Your Computer)         │
│                                         │
│  Wazuh Manager (port 1514)             │
│     ↓                                   │
│  Elasticsearch (stores logs)            │
│     ↓                                   │
│  Kibana (http://localhost:5601)        │
│  (Real-time dashboard)                 │
│     ↓                                   │
│  Ollama (AI analysis)                  │
│     ↓                                   │
│  Alert Analyzer (Discord alerts)       │
└─────────────────────────────────────────┘
```

---

## Your macbook IP

Your macbook IP is displayed in the deployment script output.
**Save this IP - you'll need it for the Raspberry Pi configuration!**

---

## Next Advanced Steps (Optional)

1. **Create Kibana visualizations** for specific threats
2. **Set up Shuffle (SOAR)** for automated response workflows
3. **Configure Discord webhooks** for team alerts
4. **Add more endpoints** (other VMs, laptops, etc.)
5. **Monitor 24/7** with dashboards

---

## Questions?

Refer to the full guides:
- `SOC_SIEM_SETUP_GUIDE.md` - Detailed explanations
- `SOC_SIEM_RPI_SETUP.md` - Raspberry Pi specific info

---

**Happy monitoring! 🎉**
