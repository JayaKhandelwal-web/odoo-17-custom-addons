# 🆘 Troubleshooting Guide - Team Leader

## 🔴 COMMON ISSUES & SOLUTIONS

---

## 1️⃣ GIT ISSUES

### Problem: "Merge conflict detected"
**Symptoms**: Developer can't push, sees conflict message

**Solution**:
```bash
cd ~/odoo17-docker/addons

# Get their branch name (e.g., dev-naman7077-dev)
git fetch origin

# Check out their branch
git checkout dev-developer-name

# Merge main into their branch
git merge main

# Fix conflicts in files (look for <<<<<<, ======, >>>>>>)
# Edit files and remove conflict markers

# After fixing
git add .
git commit -m "Resolved merge conflicts"
git push origin dev-developer-name

# Now tell developer to run:
# ./scripts/dev-push.sh "their message"
```

---

### Problem: "Authentication failed"
**Symptoms**: Can't push/pull from GitHub

**Solution**:
```bash
# Option 1: Re-enter credentials
git push origin main
# Enter: username and token

# Option 2: Update stored credentials
git config --global credential.helper store
git push origin main
# Enter credentials once, they'll be saved

# Option 3: Token expired - create new one
# Visit: https://github.com/settings/tokens
# Generate new token, use it as password
```

---

### Problem: "Working directory not clean"
**Symptoms**: Can't switch branches, uncommitted changes

**Solution**:
```bash
# See what changed
git status

# Option 1: Save changes
git stash
# Do what you need
git stash pop

# Option 2: Commit changes
git add .
git commit -m "Saving work in progress"

# Option 3: Discard changes (CAREFUL!)
git reset --hard HEAD
```

---

## 2️⃣ DOCKER ISSUES

### Problem: "Odoo container not found"
**Symptoms**: Scripts can't find Docker container

**Solution**:
```bash
cd ~/odoo17-docker

# Check containers
docker-compose ps

# If not running, start them
docker-compose up -d

# If still issues, rebuild
docker-compose down
docker-compose up -d --build
```

---

### Problem: "Docker won't restart"
**Symptoms**: `docker-compose restart` fails

**Solution**:
```bash
cd ~/odoo17-docker

# Full restart
docker-compose down
docker-compose up -d

# Check logs for errors
docker-compose logs -f

# If port conflict (8069 in use)
sudo lsof -i :8069
# Kill the process using port 8069
```

---

### Problem: "Odoo takes too long to start"
**Symptoms**: After restart, Odoo not accessible

**Solution**:
```bash
# Wait longer (Odoo can take 1-2 minutes)
# Check logs
cd ~/odoo17-docker
docker-compose logs -f odoo

# Watch for "HTTP service (werkzeug) running"
# Then access: http://localhost:8069
```

---

## 3️⃣ MODULE UPDATE ISSUES

### Problem: "Module update failed"
**Symptoms**: `update-modules.sh` shows error

**Solution**:
```bash
# Check module exists
ls -la ~/odoo17-docker/addons/MODULE_NAME

# Check module has __manifest__.py
ls -la ~/odoo17-docker/addons/MODULE_NAME/__manifest__.py

# Manual update via Odoo UI:
# 1. Go to http://localhost:8069
# 2. Apps → Remove "Apps" filter
# 3. Search module
# 4. Click "Upgrade"

# Check Odoo logs for specific error
cd ~/odoo17-docker
docker-compose logs -f odoo | grep -i error
```

---

### Problem: "Module not showing in Odoo"
**Symptoms**: Can't find module in Apps menu

**Solution**:
```bash
# Update apps list
# In Odoo: Apps → Update Apps List

# Check module path
cd ~/odoo17-docker/addons
ls -la MODULE_NAME/

# Restart Odoo
cd ~/odoo17-docker
docker-compose restart

# Check addons path in docker-compose.yml
cat docker-compose.yml | grep addons
```

---

### Problem: "Database update fails"
**Symptoms**: Error during module upgrade

**Solution**:
```bash
# Check Odoo logs
cd ~/odoo17-docker
docker-compose logs -f odoo

# Common issues:
# 1. Syntax error in Python code
# 2. Missing dependencies
# 3. Database migration issue

# Restore from backup if needed
# (Make sure you have database backups!)

# Fix code issue, then:
docker-compose restart
```

---

## 4️⃣ DEVELOPER ISSUES

### Problem: Developer says "dev-push.sh not working"
**Symptoms**: Developer can't push code

**Solution**:
```bash
# Ask developer to run:
git status
git log --oneline -5

# Common fixes:
# 1. Make script executable
chmod +x scripts/dev-push.sh

# 2. Pull latest changes first
./scripts/leader-sync.sh

# 3. Check they provided commit message
./scripts/dev-push.sh "proper message here"
```

---

### Problem: "Scripts not found"
**Symptoms**: `./scripts/script.sh: No such file`

**Solution**:
```bash
# Make sure you're in addons directory
cd ~/odoo17-docker/addons

# Check scripts exist
ls -la scripts/

# If missing, pull from GitHub
git pull origin main

# Make executable
chmod +x scripts/*.sh
```

---

## 5️⃣ NETWORK/ACCESS ISSUES

### Problem: "Can't access Odoo at localhost:8069"
**Symptoms**: Browser shows connection refused

**Solution**:
```bash
# Check if Odoo is running
cd ~/odoo17-docker
docker-compose ps

# Check if port is accessible
curl http://localhost:8069

# Check logs
docker-compose logs -f odoo

# Restart
docker-compose restart
```

---

### Problem: "GitHub repository not accessible"
**Symptoms**: 404 or permission denied

**Solution**:
```bash
# Check repository URL
git remote -v

# Should show:
# origin  https://github.com/annapurna0026-dev/odoo17-addons.git

# If wrong, update:
git remote set-url origin https://github.com/annapurna0026-dev/odoo17-addons.git

# Check you're logged in to correct account
# Visit: https://github.com/annapurna0026-dev/odoo17-addons
```

---

## 🚨 EMERGENCY RECOVERY

### NUCLEAR OPTION: Complete Reset
```bash
# 1. Backup current work
cd ~/odoo17-docker/addons
cp -r ~/odoo17-docker/addons ~/odoo17-docker/addons-emergency-backup

# 2. Clean everything
cd ~
rm -rf ~/odoo17-docker/addons

# 3. Fresh clone
git clone https://github.com/annapurna0026-dev/odoo17-addons.git ~/odoo17-docker/addons

# 4. Make scripts executable
cd ~/odoo17-docker/addons
chmod +x scripts/*.sh

# 5. Restart Docker
cd ~/odoo17-docker
docker-compose down
docker-compose up -d

# 6. Test
cd ~/odoo17-docker/addons
./scripts/leader-status.sh
```

---

## 📞 WHEN TO CONTACT SUPPORT

Contact if:
- ❌ Database corrupted
- ❌ Docker completely broken
- ❌ Lost important code
- ❌ GitHub account issues
- ❌ Server/infrastructure problems

Otherwise, try solutions above first! ✅

---

**Keep this guide handy for quick problem solving!**
