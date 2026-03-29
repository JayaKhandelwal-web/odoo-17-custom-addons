#!/bin/bash

# FULL AUTO-SYNC SCRIPT FOR TEAM LEADER
# This script does EVERYTHING automatically:
# 1. Pulls latest code from GitHub
# 2. Restarts Docker containers
# 3. Detects changed Odoo modules
# 4. Automatically upgrades modules in Odoo database
# 5. Restarts Odoo to apply changes

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 FULL AUTO-SYNC - Code + Docker + Module Upgrade"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to addons directory
cd ~/odoo17-docker/addons

# ============================================
# STEP 1: Pull Latest Code from GitHub
# ============================================
echo "📥 STEP 1/5: Pulling latest code from GitHub..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

git checkout main
git pull origin main

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Failed to pull code from GitHub!"
    echo "💡 Check your internet connection or Git credentials"
    exit 1
fi

echo "✅ Code updated successfully"
echo ""

# ============================================
# STEP 2: Detect Changed Modules
# ============================================
echo "🔍 STEP 2/5: Detecting changed modules..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get list of changed modules from last 5 commits
CHANGED_MODULES=$(git log -5 --name-only --pretty=format: | \
    grep -v "^scripts/" | \
    grep -v "^\.git" | \
    grep -v "README" | \
    grep -v "TROUBLESHOOTING" | \
    grep -v "DEVELOPER" | \
    grep -v "QUICK_REFERENCE" | \
    grep -v "\.sh$" | \
    grep "/" | \
    cut -d'/' -f1 | \
    sort -u | \
    tr '\n' ',' | \
    sed 's/,$//')

if [ -z "$CHANGED_MODULES" ]; then
    echo "ℹ️  No module changes detected in recent commits"
    SKIP_UPGRADE=true
else
    echo "📦 Changed modules detected:"
    echo "$CHANGED_MODULES" | tr ',' '\n' | sed 's/^/   - /'
    SKIP_UPGRADE=false
fi

echo ""

# ============================================
# STEP 3: Restart Docker Containers
# ============================================
echo "🐳 STEP 3/5: Restarting Docker containers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd ~/odoo17-docker
/usr/local/bin/docker-compose restart

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Failed to restart Docker containers!"
    echo "💡 Check if Docker is running: docker ps"
    exit 1
fi

echo "✅ Docker containers restarted"
echo "⏳ Waiting 15 seconds for Odoo to initialize..."
sleep 15
echo ""

# Return to addons directory
cd ~/odoo17-docker/addons

# ============================================
# STEP 4: Auto-Upgrade Modules in Odoo
# ============================================
if [ "$SKIP_UPGRADE" = false ]; then
    echo "⚡ STEP 4/5: Auto-upgrading modules in Odoo database..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Find Odoo container
    CONTAINER_ID=$(docker ps | grep odoo | grep -v postgres | awk '{print $1}')
    
    if [ -z "$CONTAINER_ID" ]; then
        echo "❌ ERROR: Odoo container not found!"
        echo "💡 Check if Odoo is running: docker ps"
        exit 1
    fi
    
    echo "🎯 Upgrading modules: $CHANGED_MODULES"
    echo ""
    
    # Run Odoo upgrade command
    docker exec -u odoo $CONTAINER_ID odoo \
        -c /etc/odoo/odoo.conf \
        -d odoo17 \
        -u $CHANGED_MODULES \
        --stop-after-init
    
    UPGRADE_STATUS=$?
    
    if [ $UPGRADE_STATUS -eq 0 ]; then
        echo ""
        echo "✅ Modules upgraded successfully"
    else
        echo ""
        echo "⚠️  WARNING: Module upgrade completed with warnings"
        echo "💡 Check Odoo logs if there are issues"
    fi
    echo ""
    
    # ============================================
    # STEP 5: Final Restart
    # ============================================
    echo "🔄 STEP 5/5: Final restart to apply changes..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    docker restart $CONTAINER_ID > /dev/null 2>&1
    
    echo "✅ Odoo restarted"
    echo "⏳ Waiting 10 seconds for Odoo to be ready..."
    sleep 10
    echo ""
else
    echo "⏭️  STEP 4/5: Skipping module upgrade (no changes detected)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⏭️  STEP 5/5: No final restart needed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

# ============================================
# COMPLETION SUMMARY
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ FULL AUTO-SYNC COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "   ✅ Code pulled from GitHub"
echo "   ✅ Docker containers restarted"

if [ "$SKIP_UPGRADE" = false ]; then
    echo "   ✅ Modules upgraded: $CHANGED_MODULES"
    echo "   ✅ Odoo restarted and ready"
else
    echo "   ℹ️  No module upgrades needed"
fi

echo ""
echo "🌐 Your Odoo is now running with the latest code!"
echo "🔗 Access at: http://localhost:8069"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show recent activity
echo ""
echo "📋 Recent Team Activity (Last 5 commits):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git log -5 --pretty=format:"%h - %an: %s (%ar)" --abbrev-commit
echo ""
echo ""
