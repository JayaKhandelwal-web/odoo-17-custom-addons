#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: Please provide module names${NC}"
    echo -e "${YELLOW}Usage: ./scripts/update-modules.sh module1 module2 module3${NC}"
    echo ""
    echo -e "${YELLOW}Example:${NC}"
    echo -e "  ./scripts/update-modules.sh fleet_booking custom_shop_features"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔄 Updating Odoo Modules...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MODULES="$@"
echo -e "${YELLOW}Modules to update: ${MODULES}${NC}"
echo ""

# Get Odoo container name
CONTAINER=$(docker ps --filter "name=odoo" --format "{{.Names}}" | head -1)

if [ -z "$CONTAINER" ]; then
    echo -e "${RED}❌ Odoo container not found!${NC}"
    echo -e "${YELLOW}Please make sure Docker is running${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Odoo container: ${CONTAINER}${NC}"

# Update modules using Odoo CLI
echo -e "${BLUE}🔄 Running module upgrade...${NC}"
docker exec -it $CONTAINER odoo -u $MODULES -d odoo --stop-after-init

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Modules updated successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}🔄 Restarting Odoo to apply changes...${NC}"
    cd ~/odoo17-docker
    docker-compose restart
    echo -e "${GREEN}✅ Odoo restarted!${NC}"
    echo -e "${YELLOW}📍 Access Odoo at: http://localhost:8069${NC}"
else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Module update failed!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Please check:${NC}"
    echo "  1. Module names are correct"
    echo "  2. Modules are installed in Odoo"
    echo "  3. Check Odoo logs for errors"
    exit 1
fi

cd ~/odoo17-docker/addons
