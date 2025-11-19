# How to Enable Repo Scope for GitHub Token

## 📍 Step-by-Step Instructions

### Step 1: Go to GitHub Token Settings

**Direct Link:** https://github.com/settings/tokens

Or navigate manually:
1. Go to **GitHub.com** and sign in
2. Click your **profile picture** (top right)
3. Click **"Settings"**
4. Scroll down in the left sidebar
5. Click **"Developer settings"** (at the bottom)
6. Click **"Personal access tokens"**
7. Click **"Tokens (classic)"**

### Step 2: Create New Token

1. Click the **"Generate new token"** button
2. Select **"Generate new token (classic)"**

### Step 3: Configure Token

Fill in the form:

**Token name:**
```
BGP Conflict Detector Push
```

**Expiration:**
- Choose: `90 days`, `1 year`, or `No expiration` (your choice)

**Select scopes:**
This is the important part! Scroll down and find:

✅ **Check the box for `repo`** 

The `repo` section includes:
- ✅ `repo` - Full control of private repositories
  - This includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`

**What `repo` scope gives you:**
- ✅ Read and write access to repositories
- ✅ Push code to repositories
- ✅ Create and delete repositories
- ✅ Manage repository settings

### Step 4: Generate Token

1. Scroll to the bottom
2. Click **"Generate token"** (green button)
3. **COPY THE TOKEN IMMEDIATELY** - It looks like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - ⚠️ **You won't see it again!**
   - ⚠️ **Save it somewhere safe!**

### Step 5: Use the New Token

After copying the token, use it to push:

```powershell
# Replace NEW_TOKEN with your new token
git remote set-url origin https://NEW_TOKEN@github.com/jalaluddinkhan1/bgp-conflict-detector.git

# Push your code
git push -u origin main
```

---

## 🎯 Quick Visual Guide

```
GitHub.com
  └─> Profile Picture (top right)
      └─> Settings
          └─> Developer settings (left sidebar, bottom)
              └─> Personal access tokens
                  └─> Tokens (classic)
                      └─> Generate new token
                          └─> Generate new token (classic)
                              └─> [Fill form]
                                  └─> ✅ Check "repo" scope
                                      └─> Generate token
                                          └─> COPY TOKEN
```

---

## 🔍 What to Look For

When you're on the token creation page, you'll see a list of scopes. Look for:

```
☐ repo
  Full control of private repositories
  This grants read/write access to code, commit statuses, repository projects, 
  collaborators, and deployment statuses for public and private repositories.
```

**Make sure this box is CHECKED ✅**

---

## ⚠️ Important Notes

1. **The `repo` scope is required** for pushing code
2. **Your current token** doesn't have this scope (that's why push fails)
3. **You need to create a NEW token** with `repo` scope
4. **You can't edit existing tokens** - must create new one
5. **Save the token** - you won't see it again!

---

## ✅ After Creating Token

Once you have the new token with `repo` scope:

```powershell
# Set remote with new token
git remote set-url origin https://YOUR_NEW_TOKEN@github.com/jalaluddinkhan1/bgp-conflict-detector.git

# Verify remote
git remote -v

# Push code
git push -u origin main
```

---

## 🆘 Still Having Issues?

If you can't find the settings:
- Direct link: https://github.com/settings/tokens
- Make sure you're logged into the correct GitHub account
- The token must be created under the account that owns the repository

