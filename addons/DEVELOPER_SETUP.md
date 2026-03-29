# 🚀 Developer Setup Guide - Odoo 17 Team Project

## 👥 For Developers: naman7077-dev, RajaKumar829891, Rituraj200221

---

## ✅ **ONE-TIME SETUP** (15-20 minutes)

### **STEP 1: Accept GitHub Invitation**

1. Check your email for invitation from `annapurna0026-dev`
2. Click **"Accept invitation"** 
3. You should now have access to: https://github.com/annapurna0026-dev/odoo17-addons

---

### **STEP 2: Create Personal Access Token**

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Settings:
   - **Note**: `Odoo Development`
   - **Expiration**: `90 days` (or No expiration)
   - **Scopes**: ✅ Check **repo** (all sub-items will auto-check)
4. Click **"Generate token"**
5. **⚠️ COPY THE TOKEN IMMEDIATELY** (starts with `ghp_...`)
6. Save it securely - you'll use this as your password!

---

### **STEP 3: Backup and Clone Repository**

Open your terminal and run:
```bash
# Navigate to addons folder
cd ~/odoo17-docker/addons

# Backup your existing work (IMPORTANT!)
cp -r ~/odoo17-docker/addons ~/odoo17-docker/addons-backup-$(date +%Y%m%d)

# Clean and prepare for clone
cd ~
rm -rf ~/odoo17-docker/addons

# Clone the repository
git clone https://github.com/annapurna0026-dev/odoo17-addons.git ~/odoo17-docker/addons

# Enter the directory
cd ~/odoo17-docker/addons
```

**When prompted for credentials:**
- Username: Your GitHub username (e.g., `naman7077-dev`)
- Password: Your personal access token (the `ghp_...` you copied)

---

### **STEP 4: Set Your Git Identity**

Choose the commands based on your username:

**For naman7077-dev:**
```bash
git config --global user.email "naman7077@example.com"
git config --global user.name "naman7077-dev"
```

**For RajaKumar829891:**
```bash
git config --global user.email "raja@example.com"
git config --global user.name "RajaKumar829891"
```

**For Rituraj200221:**
```bash
git config --global user.email "rituraj@example.com"
git config --global user.name "Rituraj200221"
```

---

### **STEP 5: Save Credentials (Recommended)**
```bash
# This saves your token so you don't need to enter it every time
git config --global credential.helper store
```

---

### **STEP 6: Verify Setup**
```bash
# Check if scripts are available
ls -la scripts/

# Make sure scripts are executable
chmod +x scripts/*.sh

# Test sync
./scripts/leader-sync.sh
```

---

## 📅 **DAILY WORKFLOW** (5 seconds per task!)

### **Morning Routine** (Before starting work)
```bash
cd ~/odoo17-docker/addons
./scripts/leader-sync.sh
```

This pulls all the latest code from the team.

---

### **During the Day**

Work normally on your Odoo modules:
- Edit files
- Test at http://localhost:8069
- No need to run any git commands manually!

---

### **Evening Routine** (End of day)
```bash
./scripts/dev-push.sh "Description of what you completed today"
```

**Examples of good commit messages:**
```bash
./scripts/dev-push.sh "Added customer invoice report feature"
./scripts/dev-push.sh "Fixed bug in fleet booking module"
./scripts/dev-push.sh "Updated employee attendance calculations"
```

**What happens automatically:**
1. ✅ Your changes are committed
2. ✅ Pushed to your personal branch
3. ✅ Automatically merged to main (if no conflicts)
4. ✅ Team gets your updates instantly!

---

## 🎯 **COMPLETE DAILY EXAMPLE**
```bash
# 9:00 AM - Start of day
cd ~/odoo17-docker/addons
./scripts/leader-sync.sh

# 9:00 AM - 5:00 PM
# Work on your modules, test, code...

# 5:00 PM - End of day
./scripts/dev-push.sh "Completed employee transfer module enhancements"

# Done! 🏠
```

---

## ⚠️ **IMPORTANT RULES**

### ✅ **DO:**
- ✅ Run `./scripts/leader-sync.sh` EVERY MORNING before starting work
- ✅ Run `./scripts/dev-push.sh "message"` EVERY EVENING after work
- ✅ Write clear, descriptive commit messages
- ✅ Test your code before pushing
- ✅ Push at least once per day

### ❌ **DON'T:**
- ❌ Don't work without syncing first
- ❌ Don't use vague messages like "update" or "fix"
- ❌ Don't push broken/untested code
- ❌ Don't forget to push at end of day
- ❌ Don't manually run git commands (use the scripts!)

---

## 🆘 **TROUBLESHOOTING**

### Problem: "Merge conflict detected"
```
⚠️  MERGE CONFLICT DETECTED!
📞 Please contact team leader
```

**Solution:**
1. Your work is safe - don't panic
2. Contact team leader: annapurna0026-dev
3. Team leader will resolve the conflict
4. Run `./scripts/leader-sync.sh` after resolution
5. Continue working normally

---

### Problem: "Authentication failed"

**Solution:**
- Make sure you're using personal access token (not password)
- If token expired, create new one at: https://github.com/settings/tokens
- Use `git config --global credential.helper store` to save it

---

### Problem: Forgot to sync before working

**Solution:**
```bash
./scripts/dev-push.sh "My current changes"
./scripts/leader-sync.sh
# If conflicts, contact team leader
```

---

## 📊 **QUICK REFERENCE**

| When | Command | Why |
|------|---------|-----|
| Morning | `./scripts/leader-sync.sh` | Get team's latest code |
| Evening | `./scripts/dev-push.sh "message"` | Share your work |
| Anytime | `git status` | See what you changed |
| Anytime | `git log --oneline -10` | See recent commits |

---

## ✅ **SETUP VERIFICATION CHECKLIST**

- [ ] GitHub invitation accepted
- [ ] Personal access token created and saved
- [ ] Repository cloned successfully
- [ ] Git identity configured (name and email)
- [ ] Scripts are executable
- [ ] Tested `./scripts/leader-sync.sh` successfully
- [ ] Ready to start work!

---

## 📞 **NEED HELP?**

Contact team leader:
- **GitHub**: annapurna0026-dev
- **Repository**: https://github.com/annapurna0026-dev/odoo17-addons

---

## 🎉 **YOU'RE READY!**

Just remember 2 commands per day:
- **Morning**: `./scripts/leader-sync.sh`
- **Evening**: `./scripts/dev-push.sh "what you did"`

Happy Coding! 🚀
