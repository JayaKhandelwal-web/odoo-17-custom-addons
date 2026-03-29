#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 Checking Changed Modules...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if there's a previous commit to compare
if ! git rev-parse HEAD~1 >/dev/null 2>&1; then
    echo -e "${YELLOW}No previous commits to compare${NC}"
    exit 0
fi

# Get changed directories (modules) from last commit
echo -e "${YELLOW}🔍 Modules changed in recent commits:${NC}"
echo ""

CHANGED_MODULES=$(git diff --name-only HEAD~5 HEAD | cut -d'/' -f1 | sort -u | grep -v -E '^(scripts|\.git|README|DEVELOPER)' | head -20)

if [ -z "$CHANGED_MODULES" ]; then
    echo -e "${GREEN}  No module changes detected${NC}"
else
    echo "$CHANGED_MODULES" | while read module; do
        if [ -d "$module" ] && [ -f "$module/__manifest__.py" ]; then
            echo -e "  ${BLUE}📦 $module${NC}"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}💡 To update these modules, run:${NC}"
    echo ""
    MODULES_LIST=$(echo "$CHANGED_MODULES" | grep -v '^$' | tr '\n' ' ')
    echo -e "  ${BLUE}./scripts/update-modules.sh $MODULES_LIST${NC}"
    echo ""
fi
