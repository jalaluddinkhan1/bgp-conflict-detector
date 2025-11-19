# Installing Docker Desktop on Windows

## Step-by-Step Installation Guide

### Step 1: Download Docker Desktop

1. **Go to Docker Desktop download page:**
   - Visit: https://www.docker.com/products/docker-desktop
   - Or direct download: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe

2. **Click "Download for Windows"**
   - The installer will download (usually ~500MB)

### Step 2: Run the Installer

1. **Double-click the downloaded installer** (`Docker Desktop Installer.exe`)

2. **Follow the installation wizard:**
   - Check "Use WSL 2 instead of Hyper-V" (recommended for Windows 10/11)
   - Check "Add shortcut to desktop" (optional)
   - Click **"Ok"** to start installation

3. **Wait for installation to complete** (5-10 minutes)
   - You may see a progress bar
   - Windows may ask for administrator permissions - click **"Yes"**

### Step 3: Restart Your Computer

- Docker Desktop will prompt you to restart
- **Save your work** and click **"Restart"**
- Or restart manually when ready

### Step 4: Start Docker Desktop

1. **After restart, find Docker Desktop:**
   - Look for the Docker Desktop icon in Start Menu
   - Or double-click the desktop shortcut

2. **First-time setup:**
   - Docker Desktop will start (whale icon in system tray)
   - You may see "Docker Desktop is starting..." message
   - Wait 1-2 minutes for it to fully start

3. **Accept the service agreement** if prompted

4. **Sign in (optional):**
   - You can sign in with Docker Hub account (optional)
   - Or click "Skip" to use without account

### Step 5: Verify Installation

Open PowerShell or Command Prompt and run:

```powershell
docker --version
docker-compose --version
```

You should see:
```
Docker version 24.0.x, build xxxxx
Docker Compose version v2.x.x
```

### Step 6: Test Docker

```powershell
docker run hello-world
```

You should see:
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

---

## System Requirements

### Minimum Requirements:
- **Windows 10 64-bit**: Pro, Enterprise, or Education (Build 19041 or higher)
- **Windows 11 64-bit**: Home or Pro version 21H2 or higher
- **WSL 2 feature** enabled
- **Virtualization** enabled in BIOS
- **4GB RAM** minimum (8GB recommended)
- **64-bit processor** with Second Level Address Translation (SLAT)

### Check Your System:

**Check Windows version:**
```powershell
winver
```

**Check if virtualization is enabled:**
```powershell
systeminfo | findstr /C:"Hyper-V Requirements"
```

Look for:
- "A hypervisor has been detected" = Good
- "Virtualization Enabled In Firmware: Yes" = Good

---

## Enable WSL 2 (If Needed)

Docker Desktop requires WSL 2. If you don't have it:

### Option 1: Automatic (Recommended)

1. Open PowerShell **as Administrator**
2. Run:
```powershell
wsl --install
```
3. Restart your computer
4. Docker Desktop will use WSL 2 automatically

### Option 2: Manual

1. Open PowerShell as Administrator
2. Run:
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```
3. Restart your computer
4. Download and install WSL2 kernel update:
   - https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
5. Set WSL 2 as default:
```powershell
wsl --set-default-version 2
```

---

## Troubleshooting

### "Docker Desktop won't start"

**Solution 1: Check WSL 2**
```powershell
wsl --status
```
Should show: "Default Version: 2"

**Solution 2: Restart Docker Desktop**
- Right-click Docker icon in system tray
- Click "Restart Docker Desktop"

**Solution 3: Check virtualization**
- Open Task Manager (Ctrl+Shift+Esc)
- Go to "Performance" tab
- Check "Virtualization" status
- If disabled, enable in BIOS

### "WSL 2 installation is incomplete"

**Solution:**
```powershell
# Update WSL
wsl --update

# Set default version
wsl --set-default-version 2

# Restart Docker Desktop
```

### "Docker daemon not running"

**Solution:**
1. Open Docker Desktop
2. Wait for it to fully start (whale icon should be steady)
3. Check system tray for Docker icon
4. If still not working, restart Docker Desktop

### "Port already in use"

**Solution:**
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

---

## After Installation

Once Docker is installed and running:

1. **Verify it works:**
   ```powershell
   docker ps
   ```
   Should show empty list (no errors)

2. **Run the BGP Conflict Detection System:**
   ```powershell
   docker-compose up -d
   python scripts/load_test_data.py
   python scripts/run_all_demos.py
   ```

---

## 📚 Additional Resources

- **Docker Desktop Documentation**: https://docs.docker.com/desktop/install/windows-install/
- **WSL 2 Documentation**: https://docs.microsoft.com/en-us/windows/wsl/install
- **Docker Hub**: https://hub.docker.com/

---

## Quick Checklist

- [ ] Downloaded Docker Desktop installer
- [ ] Ran installer and completed setup
- [ ] Restarted computer
- [ ] Started Docker Desktop
- [ ] Verified with `docker --version`
- [ ] Tested with `docker run hello-world`
- [ ] Ready to run BGP Conflict Detection System!

---

## Tips

1. **Keep Docker Desktop running** - It needs to be running to use Docker commands
2. **Check system tray** - Docker icon shows if it's running
3. **First pull is slow** - Downloading images takes time, be patient
4. **Use WSL 2** - It's faster and more efficient than Hyper-V
5. **Allocate resources** - In Docker Desktop settings, you can adjust CPU/RAM usage

---

## Still Having Issues?

1. Check Docker Desktop logs:
   - Click Docker icon → Troubleshoot → View logs

2. Check Windows Event Viewer:
   - Search "Event Viewer" → Windows Logs → Application

3. Try Docker Desktop reset:
   - Settings → Troubleshoot → Reset to factory defaults

4. Reinstall Docker Desktop:
   - Uninstall from Control Panel
   - Delete `%APPDATA%\Docker` folder
   - Reinstall from scratch

