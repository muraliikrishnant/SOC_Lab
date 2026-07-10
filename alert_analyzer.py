#!/usr/bin/env python3
import os
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import sys

# Configuration
ELASTICSEARCH_URL = "http://localhost:9200"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:cloud"
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
DISCORD_WEBHOOK = ""  # Set this before running: export DISCORD_WEBHOOK="your_url"


def ollama_post(path: str, payload: dict, timeout: int = 30):
    """Route to the local container for local models, or directly to
    Ollama Cloud (with OLLAMA_API_KEY as bearer token) for any model
    tagged "*:cloud" — cloud models aren't proxied by the local server."""
    model = payload.get("model", "")
    if model.endswith(":cloud"):
        return requests.post(
            "https://ollama.com" + path,
            json=payload,
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            timeout=timeout,
        )
    return requests.post(OLLAMA_URL + path, json=payload, timeout=timeout)

class SOCAnalyzer:
    def __init__(self):
        self.es_auth = None
        self.alert_buffer = []
        self.processed_ids = set()
        self.check_ollama_ready()
    
    def check_ollama_ready(self):
        """Verify Ollama is running and has models"""
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if not models:
                    print("⚠️  No Ollama models loaded. Run: docker compose exec ollama ollama pull nomic-embed-text")
                else:
                    print(f"✅ Ollama ready with {len(models)} model(s): {[m['name'] for m in models]}")
            else:
                print("⚠️  Ollama not responding, will retry...")
        except Exception as e:
            print(f"⚠️  Ollama check failed: {e}")
    
    def get_recent_alerts(self, minutes: int = 5) -> List[Dict]:
        """Fetch recent logs from Elasticsearch"""
        query = {
            "query": {
                "match_all": {}
            },
            "size": 50,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        try:
            response = requests.post(
                f"{ELASTICSEARCH_URL}/*/_search",
                json=query,
                timeout=10
            )
            response.raise_for_status()
            hits = response.json().get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except requests.exceptions.ConnectionError:
            return []
        except Exception as e:
            if "index_not_found_exception" not in str(e):
                print(f"⚠️  Error fetching alerts: {e}")
            return []
    
    def analyze_with_ollama(self, alert: Dict) -> str:
        """Send alert to Ollama for AI analysis"""
        alert_summary = f"""
        Agent: {alert.get('agent', {}).get('name', 'Unknown')}
        Rule: {alert.get('rule', {}).get('description', 'Unknown')}
        Level: {alert.get('rule', {}).get('level', 'Unknown')}
        """
        
        prompt = f"""As a cybersecurity analyst, analyze this security alert briefly:
{alert_summary}

Respond with:
1. Threat level (Low/Medium/High/Critical)
2. Action needed (Yes/No)"""
        
        try:
            response = ollama_post(
                "/api/generate",
                {
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("response", "Analysis unavailable")
        except Exception as e:
            return f"AI unavailable: {str(e)[:50]}"
    
    def send_discord_alert(self, alert: Dict, analysis: str):
        """Send formatted alert to Discord"""
        if not DISCORD_WEBHOOK or DISCORD_WEBHOOK == "":
            print(f"  📩 Alert: {alert.get('rule', {}).get('description', 'Unknown')} (Discord webhook not configured)")
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
                    "value": str(alert.get('rule', {}).get('level', 'N/A')),
                    "inline": True
                },
                {
                    "name": "AI Analysis",
                    "value": analysis[:500],
                    "inline": False
                }
            ],
            "footer": {"text": "SOC Lab - AI Enhanced"}
        }
        
        try:
            response = requests.post(
                DISCORD_WEBHOOK,
                json={"embeds": [embed]},
                timeout=10
            )
            response.raise_for_status()
            print(f"  ✅ Discord alert sent")
        except Exception as e:
            print(f"  ❌ Discord error: {str(e)[:50]}")
    
    def _get_color(self, level: int) -> int:
        """Convert Wazuh alert level to Discord color"""
        if level >= 15:
            return 0xFF0000  # Red
        elif level >= 10:
            return 0xFFA500  # Orange
        elif level >= 5:
            return 0xFFFF00  # Yellow
        else:
            return 0x0000FF  # Blue
    
    def run(self, check_interval: int = 30):
        """Main monitoring loop"""
        print(f"🚀 SOC Analyzer started - checking every {check_interval}s")
        print(f"📊 Elasticsearch: {ELASTICSEARCH_URL}")
        print(f"🤖 Ollama: {OLLAMA_URL}")
        print(f"💬 Discord: {'Configured' if DISCORD_WEBHOOK else 'Not configured (optional)'}")
        print("-" * 70)
        
        while True:
            try:
                alerts = self.get_recent_alerts(minutes=5)
                
                new_alerts = 0
                for alert in alerts:
                    alert_id = alert.get('id', alert.get('timestamp', ''))
                    
                    if alert_id not in self.processed_ids:
                        new_alerts += 1
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📩 New Alert")
                        print(f"  Agent: {alert.get('agent', {}).get('name', 'Unknown')}")
                        print(f"  Rule: {alert.get('rule', {}).get('description', 'Unknown')}")
                        
                        # Analyze with AI
                        analysis = self.analyze_with_ollama(alert)
                        print(f"  🤖 AI: {analysis[:150]}...")
                        
                        # Send to Discord
                        self.send_discord_alert(alert, analysis)
                        
                        self.processed_ids.add(alert_id)
                
                if new_alerts == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ No new alerts", end="\r")
                
                # Cleanup old IDs
                if len(self.processed_ids) > 1000:
                    self.processed_ids = set(list(self.processed_ids)[-500:])
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n\n❌ Analyzer stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    import os
    DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
    
    analyzer = SOCAnalyzer()
    analyzer.run(check_interval=30)
