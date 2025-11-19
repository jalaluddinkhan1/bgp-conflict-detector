# API Keys and Tokens Required

The BGP Conflict Detection System requires the following API keys/tokens:

## Required Tokens

### 1. **INFRAHUB_TOKEN** (Required)
**Purpose**: Authenticates with Infrahub to query BGP session data and detect conflicts.

**How to get it:**
1. Start Infrahub: `docker-compose up -d`
2. Access Infrahub UI at `http://localhost:8000`
3. Log in with the admin account
4. Go to **Settings** → **API Tokens** → **Create Token**
5. Copy the generated token

**Default value (for local dev)**: `06438eb2-7c35-4f8d-9a6e-1d3e5f89c4f2`
   - This is set in `docker-compose.yml` as `INFRAHUB_SECURITY_INITIAL_ADMIN_TOKEN`
   - **WARNING: Change this in production!**

**Set as environment variable:**
```bash
export INFRAHUB_TOKEN="your-token-here"
```

**Or in PowerShell:**
```powershell
$env:INFRAHUB_TOKEN="your-token-here"
```

**Or in docker-compose.yml:**
```yaml
environment:
  INFRAHUB_TOKEN: "your-token-here"
```

---

## Optional Tokens

### 2. **GITLAB_TOKEN** (Optional)
**Purpose**: Posts conflict warnings as comments on GitLab Merge Requests.

**When needed**: Only if you want automatic MR comments in GitLab CI/CD pipeline.

**How to get it:**
1. Go to GitLab → **User Settings** → **Access Tokens**
2. Create a token with `api` scope
3. Copy the token (you won't see it again!)

**Set in GitLab CI/CD:**
1. Go to your GitLab project
2. **Settings** → **CI/CD** → **Variables**
3. Add variable:
   - Key: `GITLAB_TOKEN`
   - Value: `your-gitlab-token`
   - Check "Mask variable" and "Protect variable"

**Or as environment variable:**
```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxx"
```

**Note**: The script will gracefully skip MR comments if this token is not set.

---

## Environment Variables Summary

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `INFRAHUB_TOKEN` | Yes | `18795e9c-b6db-fbff-cf87-10652e494a9a` | Infrahub API authentication |
| `INFRAHUB_URL` | No | `http://localhost:8000` | Infrahub server URL |
| `GITLAB_TOKEN` | No | None | GitLab API token for MR comments |
| `CI_MERGE_REQUEST_IID` | No | Auto-set in GitLab CI | Merge Request ID |
| `CI_PROJECT_ID` | No | Auto-set in GitLab CI | GitLab Project ID |
| `GIT_DIFF_FILES` | No | Empty | Space-separated changed files |
| `CONFLICT_WINDOW_MINUTES` | No | `5` | Time window for conflict detection |

---

## Quick Setup

### For Local Development:
```bash
# Set Infrahub token (uses default if not set)
export INFRAHUB_TOKEN="06438eb2-7c35-4f8d-9a6e-1d3e5f89c4f2"
export INFRAHUB_URL="http://localhost:8000"

# Run the system
python scripts/detect_bgp_conflicts.py
```

### For GitLab CI/CD:
Add these variables in **Settings** → **CI/CD** → **Variables**:
- `INFRAHUB_TOKEN`: Your Infrahub token
- `GITLAB_TOKEN`: Your GitLab personal access token (optional)

The `.gitlab-ci.yml` file will automatically use these variables.

---

## Security Best Practices

1. **Never commit tokens to Git** - Use environment variables or secrets management
2. **Use different tokens for dev/staging/prod**
3. **Rotate tokens regularly**
4. **Use GitLab CI/CD protected variables** for production
5. **Change the default Infrahub token** in production deployments

---

## Troubleshooting

### "Authentication failed" error:
- Check that `INFRAHUB_TOKEN` is set correctly
- Verify Infrahub is running: `curl http://localhost:8000/api/info`
- Ensure token has proper permissions in Infrahub

### "GitLab MR context not available":
- This is normal if running locally (not in GitLab CI)
- Set `GITLAB_TOKEN`, `CI_MERGE_REQUEST_IID`, and `CI_PROJECT_ID` to enable MR comments

### "Connection refused" to Infrahub:
- Start Infrahub: `docker-compose up -d`
- Wait for it to be ready: `docker-compose logs infrahub`
- Check `INFRAHUB_URL` is correct

