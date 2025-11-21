#!/usr/bin/env python3
"""
Validate BGP Conflict Detection System Setup
Checks if all files exist and dependencies are available
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {description}: {filepath}")
    return exists

def check_directory_exists(dirpath, description):
    """Check if a directory exists"""
    exists = os.path.isdir(dirpath)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {description}: {dirpath}")
    return exists

def check_python_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name)
        print(f"[OK] Python package installed: {package_name}")
        return True
    except ImportError:
        print(f"[MISSING] Python package missing: {package_name}")
        return False

def main():
    print("Validating BGP Conflict Detection System Setup")
    print("=" * 60)
    
    all_good = True
    
    # Check core files
    print("\nChecking core files...")
    files_to_check = [
        ("docker-compose.yml", "Docker Compose configuration"),
        (".gitlab-ci.yml", "GitLab CI configuration"),
        ("schemas/bgp.yml", "BGP schema definition"),
        ("requirements.txt", "Python requirements"),
        ("README.md", "README documentation"),
    ]
    
    for filepath, desc in files_to_check:
        if not check_file_exists(filepath, desc):
            all_good = False
    
    # Check scripts
    print("\nChecking scripts...")
    scripts = [
        ("scripts/detect_bgp_conflicts.py", "Main conflict detection script"),
        ("scripts/load_test_data.py", "Test data loader"),
        ("scripts/run_all_demos.py", "Demo orchestrator"),
        ("scripts/simulate_concurrent_change.py", "Concurrent change simulator"),
        ("scripts/simulate_flapping.py", "Flapping simulator"),
    ]
    
    for filepath, desc in scripts:
        if not check_file_exists(filepath, desc):
            all_good = False
    
    # Note: Conflict detection API is now part of bgp-orchestrator
    # No separate API service needed
    
    # Check config files
    print("\nChecking configuration files...")
    config_files = [
        ("configs/bgp/routers/router01.yaml", "Router 01 config"),
        ("configs/bgp/routers/router02.yaml", "Router 02 config"),
    ]
    
    for filepath, desc in config_files:
        if not check_file_exists(filepath, desc):
            all_good = False
    
    # Check Python packages
    print("\nChecking Python packages...")
    packages = [
        "httpx",
        "yaml",
        "gql",
    ]
    
    for package in packages:
        if not check_python_package(package):
            all_good = False
    
    # Check for Docker
    print("\nChecking Docker...")
    import subprocess
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"[OK] Docker installed: {result.stdout.strip()}")
        else:
            print("[ERROR] Docker not working properly")
            all_good = False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[ERROR] Docker not installed or not in PATH")
        print("   Install Docker Desktop: https://www.docker.com/products/docker-desktop")
        all_good = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("[OK] All checks passed! System is ready to run.")
        print("\nNext steps:")
        print("   1. Start infrastructure: docker-compose up -d")
        print("   2. Load test data: python scripts/load_test_data.py")
        print("   3. Run demos: python scripts/run_all_demos.py")
    else:
        print("[WARNING] Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("   - Install Docker Desktop: https://www.docker.com/products/docker-desktop")
        print("   - Install Python packages: pip install -r requirements.txt")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())

