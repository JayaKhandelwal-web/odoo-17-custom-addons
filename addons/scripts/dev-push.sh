#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get developer name
DEVELOPER=$(git config user.name)
BRANCH_NAME="dev-$(git config user.name | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Auto-Push Script for $DEVELOPER${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check for commit message
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Commit message required${NC}"
    echo -e "${YELLOW}Usage: ./scripts/dev-push.sh \"Your commit message\"${NC}"
    exit 1
fi

# Step 1: Save current work
echo -e "${BLUE}💾 Saving your changes...${NC}"
git add .
git stash

# Step 2: Pull latest from main
echo -e "${BLUE}📥 Pulling latest changes from main...${NC}"
git checkout main
git pull origin main

# Step 3: Switch to developer branch
echo -e "${BLUE}🔄 Switching to branch: $BRANCH_NAME${NC}"
git checkout -B $BRANCH_NAME

# Step 4: Apply saved work
echo -e "${BLUE}📦 Applying your changes...${NC}"
git stash pop || echo "No stashed changes"

# Step 5: Commit changes
echo -e "${BLUE}✍️  Committing: $1${NC}"
git add .
git commit -m "[$DEVELOPER] $1"

# Step 6: Push to developer branch
echo -e "${BLUE}⬆️  Pushing to $BRANCH_NAME...${NC}"
git push -u origin $BRANCH_NAME --force

# Step 7: Try auto-merge to main
echo -e "${BLUE}🔀 Attempting auto-merge to main...${NC}"
git checkout main
git pull origin main

if git merge $BRANCH_NAME --no-edit; then
    echo -e "${GREEN}✅ Auto-merge successful!${NC}"
    git push origin main
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 SUCCESS! Your work is now live on main!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}⚠️  MERGE CONFLICT DETECTED!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📞 Please contact team leader to resolve${NC}"
    git merge --abort
    git checkout $BRANCH_NAME
    exit 1
fi

# Return to developer branch
git checkout $BRANCH_NAME
echo -e "${GREEN}✅ Ready for next task!${NC}"
