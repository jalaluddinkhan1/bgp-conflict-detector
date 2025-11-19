# How to Get API Keys - Step by Step Guide

## 🔑 INFRAHUB_TOKEN (Required)

### Method 1: Use Default Token (Local Development Only)

The system comes with a default token for local development:

```
06438eb2-7c35-4f8d-9a6e-1d3e5f89c4f2
```

This is already configured in `docker-compose.yml`. **You don't need to do anything** if you're just testing locally!

### Method 2: Generate Your Own Token (Recommended for Production)

#### Step 1: Start Infrahub
```bash
docker-compose up -d
```

#### Step 2: Wait for Infrahub to be ready
```bash
# Check if Infrahub is running
curl http://localhost:8000/api/info

# Or check logs
docker-compose logs infrahub
```

#### Step 3: Access Infrahub Web UI
1. Open your browser: `http://localhost:8000`
2. You should see the Infrahub login page

#### Step 4: Log in
- **Username**: `admin` (or check docker-compose.yml for configured user)
- **Password**: Check the Infrahub documentation or use the default admin credentials

#### Step 5: Create API Token
1. Click on your profile icon (top right)
2. Go to **Settings** → **API Tokens** (or **Account Settings** → **Tokens**)
3. Click **Create Token** or **New Token**
4. Give it a name: `BGP Conflict Detector`
5. Set expiration (optional): Leave blank for no expiration
6. Select scopes/permissions: `read`, `write` (or `full_access`)
7. Click **Create** or **Generate**
8. **Copy the token immediately** - you won't be able to see it again!

#### Step 6: Use the Token
```bash
# Linux/Mac
export INFRAHUB_TOKEN="your-copied-token-here"

# Windows PowerShell
$env:INFRAHUB_TOKEN="your-copied-token-here"

# Windows CMD
set INFRAHUB_TOKEN=your-copied-token-here
```

#### Step 7: Verify Token Works
```bash
python scripts/load_test_data.py
```

If it works, you'll see: `✅ Infrahub is ready!`

---

## 🔑 GITLAB_TOKEN (Optional - Only for MR Comments)

### Step 1: Log in to GitLab
1. Go to [GitLab.com](https://gitlab.com) (or your GitLab instance)
2. Log in with your account

### Step 2: Create Personal Access Token
1. Click your profile icon (top right)
2. Go to **Preferences** → **Access Tokens**
   - Or go directly to: `https://gitlab.com/-/user_settings/personal_access_tokens`
3. Fill in the form:
   - **Token name**: `BGP Conflict Detector`
   - **Expiration date**: (optional, set a future date)
   - **Select scopes**: Check `api` (this is required)
4. Click **Create personal access token**

### Step 3: Copy the Token
1. **Copy the token immediately** - it looks like: `glpat-xxxxxxxxxxxxxxxxxxxx`
2. You won't be able to see it again after leaving the page!

### Step 4: Add to GitLab CI/CD Variables (For CI/CD Pipeline)

1. Go to your GitLab project
2. Navigate to: **Settings** → **CI/CD** → **Variables** → **Expand**
3. Click **Add variable**
4. Fill in:
   - **Key**: `GITLAB_TOKEN`
   - **Value**: `glpat-xxxxxxxxxxxxxxxxxxxx` (paste your token)
   - ✅ Check **"Mask variable"** (hides token in logs)
   - ✅ Check **"Protect variable"** (only available in protected branches)
5. Click **Add variable**

### Step 5: Use Locally (For Testing)
```bash
# Linux/Mac
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"

# Windows PowerShell
$env:GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
```

---

## 🚀 Quick Start (No Token Setup Needed)

If you just want to test the system locally, you can skip token setup entirely:

```bash
# 1. Start everything (uses default token)
docker-compose up -d

# 2. Wait for Infrahub (about 30 seconds)
# Check: curl http://localhost:8000/api/info

# 3. Load test data (uses default token from docker-compose.yml)
python scripts/load_test_data.py

# 4. Run tests
python scripts/run_all_demos.py
```

The default token `06438eb2-7c35-4f8d-9a6e-1d3e5f89c4f2` is already configured!

---

## ✅ Verify Your Tokens Work

### Test INFRAHUB_TOKEN:
```bash
# Set token
export INFRAHUB_TOKEN="your-token"

# Test connection
python -c "
from infrahub_sdk import InfrahubClientSync
client = InfrahubClientSync(address='http://localhost:8000', token='$INFRAHUB_TOKEN')
print('✅ Token works!')
"
```

### Test GITLAB_TOKEN:
```bash
# Set token
export GITLAB_TOKEN="glpat-xxxxx"

# Test connection
curl --header "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://gitlab.com/api/v4/user"
```

If you get your user info back, the token works!

---

## 🔒 Security Notes

1. **Never commit tokens to Git** - They're in `.gitignore` for a reason!
2. **Use environment variables** - Don't hardcode tokens in scripts
3. **Rotate tokens regularly** - Especially if they're exposed
4. **Use different tokens** for dev/staging/production
5. **Revoke old tokens** when no longer needed

---

## 🆘 Troubleshooting

### "Authentication failed" with Infrahub
- ✅ Check Infrahub is running: `docker-compose ps`
- ✅ Verify token is correct: Check for typos
- ✅ Check token hasn't expired
- ✅ Try the default token: `06438eb2-7c35-4f8d-9a6e-1d3e5f89c4f2`

### "GitLab MR context not available"
- ✅ This is normal if running locally (not in GitLab CI)
- ✅ Set `GITLAB_TOKEN` only if you want MR comments
- ✅ The system works fine without it!

### "Connection refused" to Infrahub
- ✅ Start Infrahub: `docker-compose up -d`
- ✅ Wait 30-60 seconds for it to start
- ✅ Check logs: `docker-compose logs infrahub`
- ✅ Verify URL: `curl http://localhost:8000/api/info`

---

## 📝 Summary

**For Local Testing:**
- ✅ No setup needed! Default token works
- ✅ Just run: `docker-compose up -d` and start testing

**For Production:**
- ✅ Generate your own `INFRAHUB_TOKEN` from Infrahub UI
- ✅ (Optional) Generate `GITLAB_TOKEN` for MR comments
- ✅ Store tokens as environment variables or CI/CD secrets

