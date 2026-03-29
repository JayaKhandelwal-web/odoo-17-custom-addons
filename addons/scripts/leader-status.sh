#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                ║${NC}"
echo -e "${CYAN}║       🎯 ODOO TEAM STATUS DASHBOARD 🎯        ║${NC}"
echo -e "${CYAN}║                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Current branch
echo -e "${YELLOW}📍 Current Branch:${NC}"
git branch --show-current
echo ""

# Recent commits
echo -e "${YELLOW}📝 Recent Team Activity (Last 15 commits):${NC}"
git log --oneline --all --graph --decorate -15
echo ""

# Active branches
echo -e "${YELLOW}🌿 Developer Branches:${NC}"
git branch -a | grep "remotes/origin/dev-" | sed 's/remotes\/origin\//  /' || echo "  No developer branches yet"
echo ""

# Uncommitted changes
echo -e "${YELLOW}🔧 Local Uncommitted Changes:${NC}"
if [[ -z $(git status --short) ]]; then
    echo "  ✅ Working directory clean"
else
    git status --short
fi
echo ""

# Team contributions today
echo -e "${YELLOW}👥 Today's Team Contributions:${NC}"
if [[ -z $(git log --since="midnight" --pretty=format:"%an: %s" --all) ]]; then
    echo "  No commits today yet"
else
    git log --since="midnight" --pretty=format:"  • %an: %s" --all
fi
echo ""

# Repository stats
echo -e "${YELLOW}📊 Repository Stats:${NC}"
echo "  Total commits: $(git rev-list --all --count)"
echo "  Contributors: $(git log --format='%an' | sort -u | wc -l)"
echo "  Branches: $(git branch -a | wc -l)"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Dashboard loaded successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
