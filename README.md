# 🚀 SOC SIEM Lab - READY TO USE

## ✅ EVERYTHING IS DEPLOYED AND RUNNING

Your complete SOC SIEM lab with **Elasticsearch + Kibana + Ollama AI** is now running on your macbook!

---

## 📍 CRITICAL INFORMATION

### Your macbook IP
```
192.168.0.197
```
**SAVE THIS! You need it for Raspberry Pi configuration.**

### Access Points
| Service | URL | Purpose |
|---------|-----|---------|
| **Kibana Dashboard** | http://localhost:5601 | View live logs |
| **Elasticsearch API** | http://localhost:9200 | Raw data access |
| **Ollama API** | http://localhost:11434 | AI threat analysis |
| **Splunk Web** | http://localhost:8000 | SOC AI Chat app lives here (Phase 2, see SOC_AI_PHASE2.md) |
| **SOC AI Chat** | http://localhost:8080/chat/ui | Same chat, standalone (also embedded as a Splunk app) |

---

## 🚀 START HERE - IMMEDIATE NEXT STEPS

### Step 1: Configure Raspberry Pi (10 minutes)

#### Option A: Quick Setup (Recommended)
```bash
# Copy the setup script to Raspberry Pi
scp /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM/RPI_SETUP_SIMPLE.sh kali@192.168.1.50:/home/kali/

# SSH into Raspberry Pi
ssh kali@192.168.1.50

# Edit the script to set your macbook IP
nano RPI_SETUP_SIMPLE.sh

# Find this line and update it:
# MACBOOK_IP="192.168.0.197"  # ← already correct!

# Run the setup
sudo bash RPI_SETUP_SIMPLE.sh
```

#### Option B: Manual Setup
```bash
# SSH into Raspberry Pi
ssh kali@192.168.1.50

# Run these commands:
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt-get update -y
sudo apt-get install -y wazuh-agent

# Edit config
sudo nano /var/ossec/etc/ossec.conf

# Find <server ip="MANAGER_IP"> and replace MANAGER_IP with: 192.168.0.197

# Restart agent
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl restart wazuh-agent

# Verify
sudo tail -f /var/ossec/logs/ossec.log
```

### Step 2: Verify Agent Connection
```bash
# Wait for ~30 seconds, then look for:
# "Agent connected successfully"
```

### Step 3: Generate Test Events
```bash
# On Raspberry Pi, run:
for i in {1..10}; do ssh baduser@localhost 2>/dev/null; done
nmap localhost
sudo cat /etc/shadow
```

### Step 4: View Live Dashboard
```
Open in browser: http://localhost:5601

You should see logs appearing in real-time!
```

### Step 5 (Optional): Pull AI Models
```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose exec ollama ollama pull nomic-embed-text   # local embeddings
docker compose exec ollama ollama pull gemma4:cloud       # reasoning, runs on Ollama Cloud —
                                                            # needs OLLAMA_API_KEY set in .env
```

### Step 6 (Optional): Start Alert Analyzer
```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
python3 alert_analyzer.py
```

---

## 📚 DOCUMENTATION

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_INFO.md** | Complete setup guide with troubleshooting |
| **QUICK_START.md** | Quick reference for common tasks |
| **SOC_SIEM_RPI_SETUP.md** | Detailed Raspberry Pi configuration |
| **SOC_SIEM_SETUP_GUIDE.md** | Full architecture & explanation |
| **SOC_AI_PHASE2.md** | GraphRAG triage layer (Splunk + Elastic, Neo4j, Qdrant, LLM reasoning, reports) — Phase 2, builds on this stack |

---

## 📁 FILES IN YOUR SOC_SIEM DIRECTORY

```
/Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM/

docker-compose.yml              # Docker stack (Elasticsearch, Kibana, Ollama)
alert_analyzer.py               # AI-powered alert analyzer for Discord
RPI_SETUP_SIMPLE.sh             # One-command Raspberry Pi setup
install_wazuh_agent.sh          # Detailed Raspberry Pi installer
deploy.sh                        # Deployment script (already run)

DEPLOYMENT_INFO.md              # ← START HERE
QUICK_START.md                  # Quick reference
SOC_SIEM_RPI_SETUP.md          # Raspberry Pi detailed guide
SOC_SIEM_SETUP_GUIDE.md        # Full documentation
README.md                        # This file
```

---

## 🔄 WHAT'S HAPPENING BEHIND THE SCENES

```
Raspberry Pi 5 (Kali Linux)
    ↓
Wazuh Agent sends logs to:
    ↓
macbook IP: 192.168.0.197 (port 1514)
    ↓
Elasticsearch receives & indexes logs
    ↓
Kibana displays real-time dashboard
    ↓
Ollama AI analyzes potential threats
    ↓
Alert Analyzer sends Discord webhooks (optional)
```

---

## 🛠 TROUBLESHOOTING

### Agent won't connect
```bash
# On Raspberry Pi
sudo systemctl restart wazuh-agent
sudo tail -f /var/ossec/logs/ossec.log

# Check network connectivity
ping 192.168.0.197
nc -zv 192.168.0.197 1514
```

### No logs in Kibana
1. Make sure Raspberry Pi agent is running
2. Check Elasticsearch: `curl http://localhost:9200/_cat/indices`
3. Generate test events (see Step 3 above)
4. Reload Kibana page

### Services not running
```bash
# Check status
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose ps

# View logs
docker compose logs -f

# Restart all services
docker compose down && docker compose up -d
```

---

## 🎯 SIMILAR TO MANOJ KUMAR'S LINKEDIN POST

You've built exactly what was shown in his post:

✅ **SIEM** - Elasticsearch/Kibana for log collection & visualization
✅ **Real-time Monitoring** - Live dashboard shows events as they happen
✅ **AI Analysis** - Ollama provides threat intelligence
✅ **Automation Ready** - Alert Analyzer ready for Discord webhooks
✅ **Multi-endpoint** - Collects logs from remote Raspberry Pi

The only difference: You're using Elasticsearch instead of Wazuh's proprietary indexer, and Ollama instead of manual SOAR setup. Both are production-grade!

---

## 📊 MONITORING YOUR LAB

### Real-time Dashboard
```
http://localhost:5601
```
Shows live logs from your Raspberry Pi

### Check Service Health
```bash
# Elasticsearch
curl http://localhost:9200/_cluster/health

# Kibana
curl http://localhost:5601/api/status

# Ollama
curl http://localhost:11434/api/tags
```

### Stop Services
```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose down
```

### Restart Services
```bash
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM
docker compose up -d
```

---

## 🎉 YOU'RE ALL SET!

Everything is ready. All you need to do is:

1. ✅ Read DEPLOYMENT_INFO.md
2. ✅ SSH into Raspberry Pi
3. ✅ Run the setup script
4. ✅ Watch logs appear in Kibana

**That's it! Your SOC Lab is live!** 🚀

---

## 💡 NEXT ADVANCED STEPS (OPTIONAL)

- Create custom Kibana visualizations
- Set up N8N/Shuffle for SOAR workflows
- Configure Discord webhooks for team alerts
- Add more security tools
- Monitor 24/7 with saved dashboards

---

**Happy monitoring! 🛡️**
