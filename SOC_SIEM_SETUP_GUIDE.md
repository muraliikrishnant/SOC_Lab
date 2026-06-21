# SOC/SIEM Lab Setup Guide - macbook + Kali Linux

## Architecture Overview
```
Kali Linux VM (Syslog Generator)
    ↓ (UDP/TCP port 514)
Wazuh Manager/Elasticsearch (macbook)
    ↓
Kibana Dashboard (macbook - localhost:5601)
    ↓
Ollama API Integration (AI Analysis)
    ↓
SOAR Orchestration (Shuffle/n8n)
    ↓
Discord/Slack Alerts
```

---

## Phase 1: Network Setup

### 1.1 Network Configuration
- **Host Machine**: macbook (macOS)
- **VM Software**: UTM, VirtualBox, or Parallels Desktop
- **Kali Linux VM**: Running on same network as macbook
- **Network Type**: Bridged or Host-only with static IPs

### 1.2 Get macbook IP
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```
You'll need this for Kali to send logs to.

---

## Phase 2: Install Wazuh (SIEM) on macbook

### 2.1 Option A: Using Docker (Recommended - Easier)
```bash
# Install Docker Desktop for Mac
# https://www.docker.com/products/docker-desktop

# Clone Wazuh docker compose
git clone https://github.com/wazuh/wazuh-docker.git
cd wazuh-docker
docker compose -f docker-compose.yml up -d
```

**Access Points:**
- Wazuh Manager: https://localhost:443
- Kibana Dashboard: http://localhost:5601
- Elasticsearch: http://localhost:9200

### 2.2 Option B: Native Installation (More Complex)
```bash
# Homebrew installation
brew tap wazuh/wazuh
brew install wazuh-manager
brew services start wazuh-manager
```

### 2.3 Initial Setup
1. Open https://localhost:443
2. Default credentials: admin / admin
3. Change password immediately
4. Note your Manager IP (used for Kali config)

---

## Phase 3: Configure Kali Linux as Log Source

### 3.1 Install Wazuh Agent on Kali
```bash
# On Kali Linux
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list
apt-get update
apt-get install wazuh-agent

# Start agent
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl start wazuh-agent
```

### 3.2 Configure Wazuh Agent (on Kali)
Edit `/var/ossec/etc/ossec.conf`:
```xml
<client>
    <server ip="YOUR_MACBOOK_IP">
        <port>1514</port>
        <protocol>tcp</protocol>
    </server>
</client>

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
```

Restart agent:
```bash
systemctl restart wazuh-agent
systemctl status wazuh-agent
```

### 3.3 Verify Agent Registration (on macbook Wazuh)
1. Go to Wazuh dashboard
2. Navigate to "Agents" section
3. Confirm Kali agent shows as "Active"

---

## Phase 4: Create Kibana Dashboard

### 4.1 Access Kibana
- URL: http://localhost:5601
- Default: elastic / changeme

### 4.2 Create Index Patterns
1. Stack Management → Index Patterns
2. Create pattern: `wazuh-alerts-*`
3. Time field: `timestamp`

### 4.3 Create Visualizations
Create these key visualizations:

**Dashboard 1: System Activity**
- Alert Timeline (Line chart)
- Top Agents (Bar chart)
- Alert Severity Distribution (Pie chart)
- Failed Login Attempts (Time series)

**Dashboard 2: Security Events**
- Rule Groups fired (Metric)
- FIM (File Integrity Monitoring) events
- Process Monitoring alerts
- Network connections detected

### 4.4 Create Master Dashboard
1. Kibana → Dashboards → Create Dashboard
2. Add all visualizations above
3. Set auto-refresh: 30 seconds
4. Save as "SOC Lab - Live Monitoring"

---

## Phase 5: Ollama AI Integration

### 5.1 Install Ollama (macbook)
```bash
# Install from https://ollama.ai/download or
brew install ollama

# Start Ollama service
ollama serve
```

### 5.2 Pull AI Models
```bash
# Pull lightweight model
ollama pull mistral
# or
ollama pull neural-chat
```

### 5.3 Test API
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Analyze this security alert: SSH brute force detected"
}'
```

---

## Phase 6: SOAR Integration (Alert Automation)

### 6.1 Option A: Using Shuffle (Recommended)
1. Install Docker container or use cloud version: https://shuffler.io/
2. Create workflow:
   - **Trigger**: Wazuh alert webhook
   - **Action**: Query Ollama for threat analysis
   - **Response**: Send to Discord

### 6.2 Option B: Using n8n
```bash
# Docker installation
docker run -it -p 5678:5678 n8nio/n8n
```

### 6.3 Create Alert Workflow
```
Wazuh Alert (Webhook)
    ↓
Extract malware hash/IP
    ↓
Query Ollama: "Analyze this threat..."
    ↓
Query VirusTotal API
    ↓
Format Discord message
    ↓
Send to Discord webhook
```

---

## Phase 7: Generate Live Logs from Kali

### 7.1 Create Test Traffic
```bash
# On Kali - SSH login attempts
for i in {1..10}; do
  sshpass -p wrongpassword ssh nonexistent@127.0.0.1 &
done

# Network scanning
nmap -sV localhost

# File access monitoring
touch /tmp/test_file && cat /tmp/test_file

# Package installation
apt-get update
```

### 7.2 Monitor in Real-time
- Watch Kibana dashboard refresh
- Check Wazuh manager for alerts
- Verify Ollama processing
- Check Discord alerts

---

## Phase 8: Docker Compose Setup (All-in-One)

Save as `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wazuh:
    image: wazuh/wazuh:latest
    ports:
      - "443:443"
      - "1514:1514"
      - "1515:1515"
      - "514:514/udp"
    environment:
      - INDEXER_URL=https://elasticsearch:9200
      - FILEBEAT_SSL_VERIFICATION_MODE=full
      - SSL_CERTIFICATE_AUTHORITIES=/etc/ssl/certs/ca.crt
    volumes:
      - wazuh-data:/var/ossec/data
    networks:
      - soc-network

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=changeme
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - soc-network

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - ELASTICSEARCH_PASSWORD=changeme
    depends_on:
      - elasticsearch
    networks:
      - soc-network

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - soc-network

volumes:
  wazuh-data:
  elasticsearch-data:
  ollama-data:

networks:
  soc-network:
    driver: bridge
```

Deploy:
```bash
docker compose -f docker-compose.yml up -d
```

---

## Phase 9: Python Script for AI-Enhanced Alerts

Create `alert_analyzer.py`:

```python
import requests
import json
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
KIBANA_URL = "http://localhost:5601"

def get_latest_alerts():
    """Fetch latest Wazuh alerts"""
    # Query Kibana/Elasticsearch for recent alerts
    es_query = {
        "query": {
            "range": {
                "timestamp": {
                    "gte": "now-5m"
                }
            }
        },
        "size": 10
    }
    # Implementation depends on your setup
    pass

def analyze_with_ollama(alert_text):
    """Send alert to Ollama for AI analysis"""
    prompt = f"""You are a cybersecurity analyst. 
    Analyze this alert and provide:
    1. Threat level (Low/Medium/High/Critical)
    2. Recommended action
    3. Root cause analysis
    
    Alert: {alert_text}"""
    
    response = requests.post(OLLAMA_URL, json={
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    })
    return response.json()["response"]

def send_discord_alert(analysis):
    """Send analyzed alert to Discord"""
    webhook_url = "YOUR_DISCORD_WEBHOOK"
    data = {
        "content": f"🚨 Security Alert\n{analysis}"
    }
    requests.post(webhook_url, json=data)

if __name__ == "__main__":
    alerts = get_latest_alerts()
    for alert in alerts:
        analysis = analyze_with_ollama(str(alert))
        send_discord_alert(analysis)
        print(f"[{datetime.now()}] Alert analyzed: {analysis[:100]}...")
```

Run continuously:
```bash
while true; do
  python3 alert_analyzer.py
  sleep 60
done
```

---

## Key Resources

- **Wazuh Docs**: https://documentation.wazuh.com/
- **Kibana Docs**: https://www.elastic.co/guide/en/kibana/current/index.html
- **Ollama Models**: https://ollama.ai/library
- **Shuffle SOAR**: https://shuffler.io/
- **n8n Workflows**: https://n8n.io/

---

## Troubleshooting

### Kali agent won't connect
```bash
# On Kali:
systemctl status wazuh-agent
journalctl -u wazuh-agent -n 50
```

### No logs showing in Kibana
- Verify Wazuh agent is active in manager
- Check Elasticsearch is running: `curl http://localhost:9200`
- Check logs at `/var/ossec/logs/ossec.log` on macbook

### Ollama API not responding
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
ollama serve
```

---

## Next Steps

1. ✅ Set up Wazuh on macbook
2. ✅ Configure Kali agent
3. ✅ Create Kibana dashboards
4. ✅ Install Ollama
5. ✅ Set up Shuffle/n8n SOAR
6. ✅ Create alert automation workflow
7. ✅ Test with real malware samples (safe!)
8. ✅ Configure Discord webhooks
9. ✅ Monitor 24/7 dashboard
