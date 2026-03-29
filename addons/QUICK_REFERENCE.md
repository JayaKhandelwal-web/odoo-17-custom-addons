# 🚀 Quick Reference Card - Team Leader

## ⚡ DAILY COMMANDS

### Morning Workflow (When Developers Push)
```bash
cd ~/odoo17-docker/addons
./scripts/leader-sync.sh          # Pull code + restart Docker
./scripts/check-changes.sh        # See what changed
./scripts/update-modules.sh MODULE_NAMES  # Update Odoo DB
```

### Check Team Status Anytime
```bash
./scripts/leader-status.sh        # Team dashboard
```

---

## 📋 ALL AVAILABLE SCRIPTS

| Script | What It Does | Example |
|--------|--------------|---------|
| `leader-sync.sh` | Pull latest code + Restart Docker | `./scripts/leader-sync.sh` |
| `check-changes.sh` | Show which modules changed | `./scripts/check-changes.sh` |
| `update-modules.sh` | Update modules in Odoo database | `./scripts/update-modules.sh fleet_booking` |
| `leader-status.sh` | View team activity dashboard | `./scripts/leader-status.sh` |

---

## 🔄 COMPLETE WORKFLOW EXAMPLE
```bash
# Developer pushed code at 9:00 AM

# Step 1: Sync (auto pulls + restarts Docker)
./scripts/leader-sync.sh

# Step 2: Check what changed
./scripts/check-changes.sh
# Output: fleet_booking, custom_shop_features

# Step 3: Update those modules
./scripts/update-modules.sh fleet_booking custom_shop_features

# Done! ✅
```

---

## 🆘 TROUBLESHOOTING

### Problem: Merge Conflict
```bash
git status                        # See conflicted files
# Edit files, remove conflict markers
git add .
git commit -m "Resolved conflicts"
git push origin main
```

### Problem: Docker Not Restarting
```bash
cd ~/odoo17-docker
docker-compose restart
docker-compose ps                 # Check status
```

### Problem: Module Update Failed
```bash
# Check Odoo logs
cd ~/odoo17-docker
docker-compose logs -f --tail=100

# Or restart everything
docker-compose down
docker-compose up -d
```

### Problem: Need to Manually Update Module
1. Go to: http://localhost:8069
2. Apps → Remove "Apps" filter
3. Search module name
4. Click "Upgrade"

---

## 🔧 USEFUL GIT COMMANDS
```bash
git status                        # See current changes
git log --oneline -10             # Recent commits
git branch -a                     # All branches
git pull origin main              # Manual pull
git push origin main              # Manual push
```

---

## 🐳 USEFUL DOCKER COMMANDS
```bash
cd ~/odoo17-docker

docker-compose ps                 # Container status
docker-compose restart            # Restart Odoo
docker-compose logs -f            # View logs
docker-compose down               # Stop all
docker-compose up -d              # Start all
```

---

## 📊 REPOSITORY INFO

- **Repository**: https://github.com/annapurna0026-dev/odoo17-addons
- **Team Leader**: annapurna0026-dev
- **Developers**: naman7077-dev, RajaKumar829891, Rituraj200221

---

## ⚡ ONE-LINER COMMANDS
```bash
# Full sync + check changes
./scripts/leader-sync.sh && ./scripts/check-changes.sh

# Sync + update all changed modules (manual module names)
./scripts/leader-sync.sh && ./scripts/update-modules.sh module1 module2

# Quick status check
./scripts/leader-status.sh

# Restart Odoo only
cd ~/odoo17-docker && docker-compose restart
```

---

## 📞 EMERGENCY PROCEDURES

### Everything Broken? Reset Workflow:
```bash
cd ~/odoo17-docker/addons
git status                        # Check state
git stash                         # Save work
git checkout main
git pull origin main              # Get latest
cd ~/odoo17-docker
docker-compose restart            # Restart Odoo
```

### Lost Work? Check Stash:
```bash
git stash list                    # See saved work
git stash pop                     # Restore last save
```

### Need Clean Start?
```bash
cd ~/odoo17-docker
docker-compose down
docker-compose up -d
cd ~/odoo17-docker/addons
./scripts/leader-sync.sh
```

---

## 💡 TIPS

- ✅ Run `leader-sync.sh` every morning
- ✅ Check `leader-status.sh` to monitor team
- ✅ Always update modules after syncing code
- ✅ Test in Odoo after module updates
- ✅ Communicate with developers about conflicts

---

## 🎯 DEVELOPER WORKFLOW REMINDER

Developers should run:
- **Morning**: `./scripts/leader-sync.sh`
- **Evening**: `./scripts/dev-push.sh "what they did"`

Their code auto-merges if no conflicts!

---

**Print this page and keep it at your desk!** 📄
