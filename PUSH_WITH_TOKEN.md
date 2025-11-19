# Push to GitHub - Use Personal Access Token

## ⚠️ Important: GitHub No Longer Accepts Passwords

GitHub stopped accepting passwords for Git operations in August 2021. You **must** use a **Personal Access Token** instead.

## 🔑 Create Personal Access Token

### Step 1: Go to GitHub Token Settings
Visit: **https://github.com/settings/tokens**

### Step 2: Generate New Token
1. Click **"Generate new token"** → **"Generate new token (classic)"**
2. Fill in:
   - **Note**: `BGP Conflict Detector`
   - **Expiration**: Choose (90 days, 1 year, or no expiration)
   - **Select scopes**: Check ✅ **`repo`** (full control of private repositories)
3. Click **"Generate token"** at the bottom
4. **COPY THE TOKEN** - It looks like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - ⚠️ You won't see it again!

### Step 3: Use Token as Password

When you push, Git will ask for credentials:
- **Username**: `jalaluddinkhan1`
- **Password**: **Paste your Personal Access Token** (NOT your GitHub password)

## 🚀 Push Commands

```powershell
# Make sure remote is set
git remote add origin https://github.com/jalaluddinkhan1/bgp-conflict-detector.git

# Set branch to main
git branch -M main

# Push (will ask for username and token)
git push -u origin main
```

When prompted:
- Username: `jalaluddinkhan1`
- Password: `ghp_your_token_here` (paste your token)

## ✅ Alternative: Use Token in URL (One-time)

If you want to avoid entering credentials each time:

```powershell
# Replace YOUR_TOKEN with your actual token
git remote set-url origin https://YOUR_TOKEN@github.com/jalaluddinkhan1/bgp-conflict-detector.git

# Now push (won't ask for credentials)
git push -u origin main
```

## 🔒 Security Note

**Never share your Personal Access Token!** It's like a password. If you accidentally share it, revoke it immediately and create a new one.

