# SOC/SIEM Lab Setup - macbook + Raspberry Pi 5 Kali

## Architecture (REMOTE ENDPOINT)
```
Raspberry Pi 5 (Kali Linux - Remote)
    ↓ (Network: TCP/UDP port 514/1514)
macbook (Local Network)
    ├─ Wazuh Manager (receives logs)
    ├─ Elasticsearch (stores logs)
    ├─ Kibana (http://localhost:5601)
    ├─ Ollama (AI analysis)
    └─ SOAR (Shuffle/n8n)
        ↓
    Discord/Slack Alerts
```

---

## Phase 0: Network Prerequisites

### 0.1 Network Setup Requirements
✅ Raspberry Pi 5 and macbook on **same network** (WiFi or Ethernet)
✅ Both devices can ping each other
✅ No firewall blocking port 514/1514

### 0.2 Find Your macbook IP (Server)
```bash
# On macbook
ifconfig | grep "inet " | grep -v 127.0.0.1

# Example output:
# inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
```
**Keep this IP handy - you'll need it for Raspberry Pi configuration**

### 0.3 Find Raspberry Pi IP (Client)
```bash
# On Raspberry Pi
hostname -I
# Example: 192.168.1.50

# Test ping from Raspberry Pi to macbook
ping 192.168.1.100
```

### 0.4 Allow macbook Firewall
```bash
# On macbook - allow incoming logs
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/docker
```

Or use System Preferences:
- System Settings → Privacy & Security → Firewall
- Add Docker/Wazuh to allowed apps

---

## Phase 1: Deploy Wazuh Stack on macbook

### 1.1 Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

### 1.2 Create docker-compose.yml

Save this as `~/SOC_SIEM/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # Wazuh Manager - receives logs from agents
  wazuh-manager:
    image: wazuh/wazuh:latest
    hostname: wazuh-manager
    restart: always
    ports:
      - "1514:1514"  # Agent communication
      - "1515:1515"  # Agent registration
      - "514:514/udp"  # Syslog
      - "443:443"    # HTTPS UI
    environment:
      - INDEXER_URL=https://elasticsearch:9200
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=SecurePassword123!
      - FILEBEAT_SSL_VERIFICATION_MODE=full
      - SSL_CERTIFICATE_AUTHORITIES=/etc/ssl/certs/ca.crt
    volumes:
      - wazuh-data:/var/ossec/data
      - wazuh-config:/var/ossec/etc
      - wazuh-logs:/var/ossec/logs
    networks:
      - soc-network
    depends_on:
      - elasticsearch

  # Elasticsearch - stores indexed logs
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    hostname: elasticsearch
    restart: always
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.enrollment.enabled=true
      - ELASTIC_PASSWORD=SecurePassword123!
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # For macbook
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - soc-network
    healthcheck:
      test: curl -s http://localhost:9200 >/dev/null || exit 1
      interval: 10s
      timeout: 10s
      retries: 5

  # Kibana - Dashboard visualization
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    hostname: kibana
    restart: always
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - ELASTICSEARCH_PASSWORD=SecurePassword123!
    depends_on:
      - elasticsearch
    networks:
      - soc-network
    healthcheck:
      test: curl -s http://localhost:5601 >/dev/null || exit 1
      interval: 10s
      timeout: 10s
      retries: 5

  # Ollama - AI threat analysis
  ollama:
    image: ollama/ollama:latest
    hostname: ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - soc-network
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

volumes:
  wazuh-data:
  wazuh-config:
  wazuh-logs:
  elasticsearch-data:
  ollama-data:

networks:
  soc-network:
    driver: bridge
```

### 1.3 Deploy Stack
```bash
cd ~/SOC_SIEM
docker compose -f docker-compose.yml up -d

# Wait 2-3 minutes for services to start
sleep 180

# Check status
docker compose -f docker-compose.yml ps

# Expected: All services "Up"
```

### 1.4 Verify macbook Services
```bash
# Wazuh Manager
curl -k https://localhost:443/api/version

# Elasticsearch
curl http://localhost:9200/_cluster/health

# Kibana
curl http://localhost:5601/api/status

# Ollama
curl http://localhost:11434/api/tags
```

---

## Phase 2: Configure Raspberry Pi 5 as Log Source

### 2.1 Prerequisites on Raspberry Pi
```bash
# SSH into Raspberry Pi
ssh kali@192.168.1.50

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl gnupg lsb-release
```

### 2.2 Install Wazuh Agent on Raspberry Pi
```bash
# Add Wazuh repository
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list

# Update and install
sudo apt update
sudo apt install -y wazuh-agent

# Start and enable
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl start wazuh-agent

# Verify
sudo systemctl status wazuh-agent
```

### 2.3 Configure Wazuh Agent
Edit Wazuh agent config:
```bash
sudo nano /var/ossec/etc/ossec.conf
```

Find the `<client>` section and replace/update with:

```xml
<client>
    <server ip="192.168.1.100">
        <port>1514</port>
        <protocol>tcp</protocol>
    </server>
    <config-profile>generic, linux, local</config-profile>
</client>

<!-- Monitor system logs -->
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

<!-- Monitor system processes -->
<localfile>
    <location>/var/log/kern.log</location>
    <log_format>syslog</log_format>
</localfile>

<!-- FIM - File Integrity Monitoring -->
<localfile>
    <location>/etc/passwd</location>
    <log_format>syslog</log_format>
</localfile>

<localfile>
    <location>/etc/shadow</location>
    <log_format>syslog</log_format>
</localfile>

<!-- Monitor suspicious activity -->
<localfile>
    <location>/var/log/sudo.log</location>
    <log_format>syslog</log_format>
</localfile>

<!-- Monitor Kali tools usage -->
<localfile>
    <location>/var/log/metasploit.log</location>
    <log_format>syslog</log_format>
</localfile>
```

**Replace `192.168.1.100` with YOUR macbook IP address!**

### 2.4 Restart Agent
```bash
# On Raspberry Pi
sudo systemctl restart wazuh-agent

# Check status
sudo systemctl status wazuh-agent

# View logs
sudo tail -f /var/ossec/logs/ossec.log
```

### 2.5 Verify Connection (optional)
```bash
# On Raspberry Pi - test connection to macbook
nc -zv 192.168.1.100 1514

# Expected: "Connection to 192.168.1.100 1514 port [tcp/*] succeeded"
```

---

## Phase 3: Register Agent in Wazuh Manager

### 3.1 Access Wazuh Web UI
- URL: https://localhost:443
- Default credentials: admin / admin
- ⚠️ Accept self-signed certificate warning

### 3.2 Register Agent
1. Left sidebar → **Agents**
2. Click **Deploy new agent**
3. Select **Linux** as OS
4. Copy the agent key/registration command
5. Run on Raspberry Pi:
```bash
sudo /var/ossec/bin/wazuh-control restart
```

### 3.3 Verify Agent Connection
In Wazuh UI:
1. Agents section
2. Look for agent with Raspberry Pi hostname
3. Status should show: **Active** ✅
4. Connection time shows recent timestamp

---

## Phase 4: Generate Live Logs from Raspberry Pi

### 4.1 Create Test Events
```bash
# On Raspberry Pi

# Failed SSH attempts
for i in {1..5}; do
  ssh baduser@localhost -p 22 2>/dev/null &
done

# Package installation
sudo apt install -y curl wget htop

# File access
sudo cat /etc/shadow

# Network scan
nmap localhost

# Process monitoring
ps aux

# Sudo usage
sudo whoami
```

### 4.2 Monitor in Real-time (on macbook)
```bash
# Watch Wazuh agent traffic
docker compose logs -f wazuh-manager

# Or check Elasticsearch
curl -s http://localhost:9200/wazuh-alerts-*/_search | jq '.hits.hits[] | .fields'
```

---

## Phase 5: Create Kibana Dashboard

### 5.1 Access Kibana
- URL: http://localhost:5601
- Credentials: elastic / SecurePassword123!

### 5.2 Create Index Pattern
1. Stack Management → Data Views
2. Create data view: `wazuh-alerts-*`
3. Time field: `timestamp`
4. Save

### 5.3 Create Visualizations

**Visualization 1: Alert Timeline**
- Type: Line chart
- X-axis: Timestamp (5 min intervals)
- Y-axis: Count
- Title: "Alerts Over Time"

**Visualization 2: Top Agents**
- Type: Bar chart
- Metric: Document count
- Group by: `agent.name`
- Title: "Logs by Agent"

**Visualization 3: Alert Severity**
- Type: Pie chart
- Metric: Count
- Group by: `rule.level`
- Title: "Alert Severity Distribution"

**Visualization 4: Failed Logins**
- Type: Table
- Filter: `rule.description:"failed"`
- Columns: timestamp, agent.name, rule.description
- Title: "Failed SSH Attempts"

### 5.4 Create Master Dashboard
1. Kibana → Dashboards → Create Dashboard
2. Add all 4 visualizations above
3. Set refresh: 30 seconds
4. Save as "SOC Lab - Pi + macbook"

---

## Phase 6: AI Integration with Ollama

### 6.1 Pull AI Models on macbook
```bash
# This runs inside docker, so:
docker compose exec ollama ollama pull mistral
docker compose exec ollama ollama pull neural-chat

# Verify
docker compose exec ollama ollama list
```

### 6.2 Test Ollama API
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "A security alert detected 5 failed SSH login attempts to user root. What is the threat level?",
  "stream": false
}'
```

---

## Phase 7: Create Alert Automation Script

### 7.1 Python Alert Analyzer
Save as `~/SOC_SIEM/alert_analyzer.py`:

```python
#!/usr/bin/env python3
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Configuration
ELASTICSEARCH_URL = "http://localhost:9200"
OLLAMA_URL = "http://localhost:11434"
DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL"  # Get from Discord
ELASTICSEARCH_USER = "elastic"
ELASTICSEARCH_PASS = "SecurePassword123!"

class SOCAnalyzer:
    def __init__(self):
        self.es_auth = (ELASTICSEARCH_USER, ELASTICSEARCH_PASS)
        self.alert_buffer = []
    
    def get_recent_alerts(self, minutes: int = 5) -> List[Dict]:
        """Fetch recent Wazuh alerts from Elasticsearch"""
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": f"now-{minutes}m"
                    }
                }
            },
            "size": 50,
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        try:
            response = requests.post(
                f"{ELASTICSEARCH_URL}/wazuh-alerts-*/_search",
                json=query,
                auth=self.es_auth,
                timeout=10
            )
            response.raise_for_status()
            hits = response.json().get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            return []
    
    def analyze_with_ollama(self, alert: Dict) -> str:
        """Send alert to Ollama for AI analysis"""
        alert_summary = f"""
        Alert from: {alert.get('agent', {}).get('name', 'Unknown')}
        Rule: {alert.get('rule', {}).get('description', 'Unknown')}
        Severity: {alert.get('rule', {}).get('level', 'Unknown')}
        Event: {alert.get('data', {}).get('srcip', 'N/A')} -> {alert.get('data', {}).get('dstip', 'N/A')}
        """
        
        prompt = f"""As a cybersecurity analyst, analyze this security alert and respond briefly:

{alert_summary}

Provide:
1. Threat Level (Low/Medium/High/Critical)
2. One-line recommended action
3. Is investigation needed? (Yes/No)"""
        
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("response", "Analysis unavailable")
        except Exception as e:
            print(f"Error contacting Ollama: {e}")
            return f"Error: {e}"
    
    def send_discord_alert(self, alert: Dict, analysis: str):
        """Send formatted alert to Discord"""
        if not DISCORD_WEBHOOK or DISCORD_WEBHOOK == "YOUR_DISCORD_WEBHOOK_URL":
            print("[DEMO] Would send to Discord (webhook not configured)")
            return
        
        embed = {
            "title": f"🚨 {alert.get('rule', {}).get('description', 'Security Alert')}",
            "color": self._get_color(alert.get('rule', {}).get('level', 3)),
            "fields": [
                {
                    "name": "Agent",
                    "value": alert.get('agent', {}).get('name', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "Severity",
                    "value": alert.get('rule', {}).get('level', 'N/A'),
                    "inline": True
                },
                {
                    "name": "AI Analysis",
                    "value": analysis[:500],  # Truncate long analysis
                    "inline": False
                },
                {
                    "name": "Timestamp",
                    "value": alert.get('timestamp', 'N/A'),
                    "inline": True
                }
            ],
            "footer": {"text": "SOC Lab - AI-Enhanced Alerting"}
        }
        
        try:
            response = requests.post(
                DISCORD_WEBHOOK,
                json={"embeds": [embed]},
                timeout=10
            )
            response.raise_for_status()
            print(f"✅ Discord alert sent for: {alert.get('rule', {}).get('description', 'Alert')}")
        except Exception as e:
            print(f"Error sending Discord alert: {e}")
    
    def _get_color(self, level: int) -> int:
        """Convert Wazuh alert level to Discord color"""
        if level >= 15:
            return 0xFF0000  # Red - Critical
        elif level >= 10:
            return 0xFFA500  # Orange - High
        elif level >= 5:
            return 0xFFFF00  # Yellow - Medium
        else:
            return 0x0000FF  # Blue - Low
    
    def run(self, check_interval: int = 60):
        """Main loop"""
        print(f"🚀 SOC Analyzer started - checking every {check_interval}s")
        print(f"📊 Elasticsearch: {ELASTICSEARCH_URL}")
        print(f"🤖 Ollama: {OLLAMA_URL}")
        print(f"💬 Discord: {'Configured' if DISCORD_WEBHOOK != 'YOUR_DISCORD_WEBHOOK_URL' else 'Not configured'}")
        print("-" * 60)
        
        processed_ids = set()
        
        while True:
            try:
                alerts = self.get_recent_alerts(minutes=5)
                
                for alert in alerts:
                    alert_id = alert.get('id', alert.get('timestamp', ''))
                    
                    # Avoid reprocessing
                    if alert_id not in processed_ids:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📩 New alert: {alert.get('rule', {}).get('description', 'Unknown')}")
                        
                        # Analyze with AI
                        analysis = self.analyze_with_ollama(alert)
                        print(f"🤖 Analysis: {analysis[:200]}...")
                        
                        # Send to Discord
                        self.send_discord_alert(alert, analysis)
                        
                        processed_ids.add(alert_id)
                
                # Clean old IDs to prevent memory bloat
                if len(processed_ids) > 1000:
                    processed_ids = set(list(processed_ids)[-500:])
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n❌ Analyzer stopped")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    analyzer = SOCAnalyzer()
    analyzer.run(check_interval=30)  # Check every 30 seconds
```

### 7.2 Run Alert Analyzer
```bash
# Install dependencies
pip3 install requests

# Make executable
chmod +x ~/SOC_SIEM/alert_analyzer.py

# Run in background
nohup python3 ~/SOC_SIEM/alert_analyzer.py > ~/SOC_SIEM/analyzer.log &

# Or run in screen for monitoring
screen -S soc-analyzer
python3 ~/SOC_SIEM/alert_analyzer.py

# Detach: Ctrl+A, then D
# Reattach: screen -r soc-analyzer
```

---

## Phase 8: Complete Workflow Test

### 8.1 Start Everything (on macbook)
```bash
# Ensure Docker containers running
docker compose -f ~/SOC_SIEM/docker-compose.yml up -d

# Wait for services
sleep 60

# Start analyzer
nohup python3 ~/SOC_SIEM/alert_analyzer.py > ~/SOC_SIEM/analyzer.log &

# Verify all running
docker compose ps
```

### 8.2 Generate Test Events (on Raspberry Pi)
```bash
# SSH into Raspberry Pi and create suspicious activity
for i in {1..10}; do
  ssh invalid_user@localhost 2>/dev/null
done

# Monitor file changes
sudo cat /etc/passwd

# Network activity
nmap -sV localhost
```

### 8.3 Monitor Live
**Dashboard (macbook):**
- Open http://localhost:5601
- Watch alerts appear in real-time
- Refresh every 30 seconds

**Console (macbook):**
```bash
tail -f ~/SOC_SIEM/analyzer.log
```

**Discord:**
- Check your Discord channel for alerts
- Each alert shows AI analysis + severity

---

## Troubleshooting (Raspberry Pi Specific)

### Agent Won't Connect
```bash
# On Raspberry Pi
sudo systemctl status wazuh-agent
sudo journalctl -u wazuh-agent -n 100

# Test network connection
nc -zv 192.168.1.100 1514

# Check if firewall on macbook is blocking
# Try: System Settings → Firewall → Add Docker to allowed apps
```

### High CPU/Memory on Pi
```bash
# Check resource usage
htop

# Reduce logging if needed
# Edit /var/ossec/etc/ossec.conf and reduce monitored locations
```

### No Logs Appearing
1. Check Wazuh agent is Active in UI
2. Verify agent key is correct
3. Restart agent: `sudo systemctl restart wazuh-agent`
4. Check Elasticsearch: `curl http://localhost:9200/_cat/indices`

### Ollama Slow
- Mistral is ~7GB (might be heavy for network)
- Try smaller model: `docker compose exec ollama ollama pull phi`
- Or pull from Pi directly to save bandwidth

---

## Network Diagram (Your Setup)

```
┌─────────────────────┐
│   Raspberry Pi 5    │
│   (Kali Linux)      │
│   192.168.1.50      │
│                     │
│  Wazuh Agent        │
│  (sends logs)       │
└──────────┬──────────┘
           │
           │ TCP 1514
           │ (network)
           │
┌──────────▼──────────────────────────────────────┐
│         macbook (192.168.1.100)                │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  Docker Stack                            │ │
│  │  ├─ Wazuh Manager (port 1514)           │ │
│  │  ├─ Elasticsearch (9200)                │ │
│  │  ├─ Kibana Dashboard (5601)             │ │
│  │  └─ Ollama AI (11434)                   │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Alert Analyzer Script                        │
│  └─ Sends to Discord webhook                 │
└─────────────────────────────────────────────┘
```

---

## Next Steps Checklist

- [ ] Deploy Docker stack on macbook
- [ ] Install Wazuh agent on Raspberry Pi
- [ ] Register agent in Wazuh UI
- [ ] Verify agent shows as Active
- [ ] Create Kibana visualizations
- [ ] Pull Ollama models
- [ ] Configure Discord webhook
- [ ] Run alert_analyzer.py
- [ ] Generate test events
- [ ] Watch alerts flow: Pi → macbook → Kibana → Ollama → Discord 🎉

---

## Security Notes

⚠️ This is a lab environment. For production:
- Change all default passwords
- Use proper SSL certificates
- Enable authentication on Elasticsearch
- Restrict firewall rules
- Use VPN for remote connections
- Never expose Wazuh directly to internet
