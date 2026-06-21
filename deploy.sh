#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SOC SIEM Lab - Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Get macbook IP
MACBOOK_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
echo -e "${GREEN}✅ macbook IP detected: ${MACBOOK_IP}${NC}\n"

# Navigate to SOC_SIEM directory
cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM/

echo -e "${BLUE}Starting Docker containers...${NC}"
docker compose -f docker-compose.yml down 2>/dev/null
docker compose -f docker-compose.yml up -d

echo -e "\n${YELLOW}⏳ Waiting 60 seconds for services to start...${NC}"
sleep 60

echo -e "\n${BLUE}Checking service status...${NC}"
docker compose ps

echo -e "\n${BLUE}Testing services...${NC}"

# Test Wazuh
if curl -sk https://localhost:443/api/version &>/dev/null; then
    echo -e "${GREEN}✅ Wazuh Manager: Running${NC}"
else
    echo -e "${YELLOW}⏳ Wazuh Manager: Still starting (can take 2+ minutes)${NC}"
fi

# Test Elasticsearch
if curl -s http://localhost:9200/_cluster/health &>/dev/null; then
    echo -e "${GREEN}✅ Elasticsearch: Running${NC}"
else
    echo -e "${YELLOW}⏳ Elasticsearch: Still starting${NC}"
fi

# Test Kibana
if curl -s http://localhost:5601/api/status &>/dev/null; then
    echo -e "${GREEN}✅ Kibana: Running${NC}"
else
    echo -e "${YELLOW}⏳ Kibana: Still starting${NC}"
fi

# Test Ollama
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo -e "${GREEN}✅ Ollama: Running${NC}"
else
    echo -e "${YELLOW}⏳ Ollama: Still starting${NC}"
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}NEXT STEPS:${NC}\n"

echo -e "${BLUE}1. Configure Raspberry Pi Wazuh Agent:${NC}"
echo -e "   Edit: /var/ossec/etc/ossec.conf on Raspberry Pi"
echo -e "   Set: <server ip=\"${MACBOOK_IP}\">"
echo -e "   Command: sudo systemctl restart wazuh-agent\n"

echo -e "${BLUE}2. Access Dashboards (on macbook):${NC}"
echo -e "   Wazuh: https://localhost:443 (admin/admin)"
echo -e "   Kibana: http://localhost:5601 (elastic/SecurePassword123!)"
echo -e "   Ollama API: http://localhost:11434\n"

echo -e "${BLUE}3. Pull Ollama Models:${NC}"
echo -e "   ${YELLOW}docker compose exec ollama ollama pull mistral${NC}\n"

echo -e "${BLUE}4. Start Alert Analyzer (in new terminal):${NC}"
echo -e "   ${YELLOW}cd /Users/mthirumalai/Documents/Personal/Claude/SOC_SIEM${NC}"
echo -e "   ${YELLOW}python3 alert_analyzer.py${NC}\n"

echo -e "${BLUE}5. Generate Test Events (on Raspberry Pi):${NC}"
echo -e "   ${YELLOW}for i in {1..10}; do ssh invalid_user@localhost 2>/dev/null; done${NC}\n"

echo -e "${GREEN}🎉 Your SOC Lab is ready!${NC}\n"
