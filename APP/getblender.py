#!/usr/bin/env python3
"""
getblender.py - Robust Cross-Platform Blender Downloader and Environment Manager
Supports: Linux, macOS, Native Windows, and Windows Subsystem for Linux (WSL/WSL2)
"""

import os
import sys
import re
import shutil
import platform
import subprocess
import urllib.request
import zipfile
import tarfile
import argparse
from pathlib import Path

# --- Configuration & Defaults ---
DEFAULT_KEEP = 2
DEFAULT_VERSION = "5.1"

def load_makerc():
    """Parses local .makerc and parent .makerc files to resolve environment variables."""
    config = {}
    for rc_path in ['.makerc', '../.makerc', '../../.makerc']:
        if os.path.exists(rc_path):
            try:
                with open(rc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, val = line.split('=', 1)
                            # Strip whitespace, quotes, and carriage returns
                            config[key.strip()] = val.strip().strip('"').strip("'").strip()
            except Exception as e:
                print(f"Warning: Failed to parse {rc_path}: {e}")
    return config

def parse_arguments():
    """Parses command-line arguments to allow easy, cross-platform overrides."""
    parser = argparse.ArgumentParser(
        description="Robust Cross-Platform Blender Downloader and Environment Manager"
    )
    # Allow both a quick positional argument (e.g. python getblender.py 5.1) or an explicit flag
    parser.add_argument(
        "pos_version",
        nargs="?",
        help="Blender version to download (e.g. 5.1 or 5.1.2). Overrides env and config.",
        default=None
    )
    parser.add_argument(
        "-v", "--version",
        help="Blender version to download (alternative to positional argument).",
        default=None
    )
    parser.add_argument(
        "-k", "--keep",
        type=int,
        help="Number of versions to keep. Overrides env and config.",
        default=None
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Suppress opening the download folder after extraction.",
        default=None
    )
    return parser.parse_args()

# Parse arguments and load configurations
args = parse_arguments()
config_vars = load_makerc()

# 1. Resolve Blender Version (CLI Arg -> Env -> .makerc -> Default)
cli_version = args.version or args.pos_version
B3DVERSION = cli_version or os.environ.get('B3DVERSION') or config_vars.get('B3DVERSION') or DEFAULT_VERSION

# 2. Resolve Keep count (CLI Arg -> Env -> .makerc -> Default)
cli_keep = args.keep
KEEP_val = cli_keep if cli_keep is not None else (os.environ.get('KEEP') or config_vars.get('KEEP'))
KEEP = int(KEEP_val) if KEEP_val is not None else DEFAULT_KEEP

# 3. Resolve No Open flag (CLI Arg -> Env -> .makerc -> Default)
if args.no_open is True:
    NO_OPEN = "true"
else:
    NO_OPEN = os.environ.get('NO_OPEN') or config_vars.get('NO_OPEN') or "false"

# Resolve Folder open flag
OPEN_FOLDER = False if NO_OPEN.lower() in ("true", "1") else True

print(f"Keeping {KEEP} versions. Will remove oldest.")

def fetch_url(url):
    """Robust scraper with SSL bypass and fallback headers simulating a modern browser."""
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    req = urllib.request.Request(url, headers={'User-Agent': user_agent})
    try:
        # Create unverified context to bypass TLS/SSL handshake errors on older machines
        import ssl
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        # Fallback to standard request
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as err:
            print(f"Network Error fetching URL {url}: {err}")
            return ""

def is_wsl():
    """Detects if Python is running inside WSL."""
    if platform.system() == "Linux":
        try:
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    return True
        except:
            pass
    return False

# --- Platform Resolution ---
sys_platform = platform.system()
sys_arch = platform.machine()
IS_WSL = is_wsl()

print(f"Detected Platform: {sys_platform} ({sys_arch}) [WSL: {IS_WSL}]")

# Setup downloads directory
if IS_WSL:
    # Query Windows Host user profile directory
    try:
        win_profile = subprocess.check_output(['cmd.exe', '/C', 'echo %USERPROFILE%'], text=True).strip()
        # Convert path to WSL POSIX path
        wsl_profile = subprocess.check_output(['wslpath', win_profile], text=True).strip()
        DOWNLOADS = os.path.join(wsl_profile, 'Downloads', f'BLENDER_{B3DVERSION}')
        # Get Windows absolute path for registering
        DOWNLOADWSL = subprocess.check_output(['wslpath', '-w', DOWNLOADS], text=True).strip()
    except Exception as e:
        print(f"Warning: Failed to map WSL paths back to Windows host: {e}")
        DOWNLOADS = os.path.expanduser(f'~/Downloads/BLENDER_{B3DVERSION}')
        DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "win64"
    EXPLORER = "explorer.exe"
elif sys_platform == "Windows":
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    DOWNLOADS = os.path.join(user_profile, 'Downloads', f'BLENDER_{B3DVERSION}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "win64"
    EXPLORER = "explorer.exe"
elif sys_platform == "Darwin":
    DOWNLOADS = os.path.expanduser(f'~/Downloads/BLENDER_{B3DVERSION}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "macos"
    EXPLORER = "open"
else:
    DOWNLOADS = os.path.expanduser(f'~/Downloads/BLENDER_{B3DVERSION}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "linux"
    EXPLORER = "xdg-open"

os.makedirs(DOWNLOADS, exist_ok=True)

# --- Version Matching logic ---
# Strip point releases if requested
m = re.match(r'^([0-9]+\.[0-9]+)', B3DVERSION)
VERSION_NUMERIC = m.group(1) if m else B3DVERSION

if re.match(r'^[0-9]+\.[0-9]+\.[0-9]+', B3DVERSION):
    # Precise point version (e.g. 5.1.1)
    SEARCH_VER_PATTERN = B3DVERSION.replace('.', r'\.')
else:
    # Base version (e.g. 5.1) -> locate highest matching point release (5.1.x)
    SEARCH_VER_PATTERN = VERSION_NUMERIC.replace('.', r'\.') + r'\.[0-9]+'

BLENDER_FILE = ""
BLENDER_URL = ""
SOURCE_TYPE = ""

# 1. First, search on download.blender.org for stable releases
print(f"Searching stable archives for version: {VERSION_NUMERIC}...")
STABLE_FOLDER_URL = f"https://download.blender.org/release/Blender{VERSION_NUMERIC}/"
stable_html = fetch_url(STABLE_FOLDER_URL)

if stable_html:
    # Extract unique archive links
    links = re.findall(r'href="([^"]+)"', stable_html)
    matching_archives = []
    
    for link in links:
        filename = link.split('/')[-1]
        # Ignore source code, checksums, and benchmark files
        if "source" in filename.lower() or "sha256" in filename.lower() or "benchmark" in filename.lower():
            continue
            
        if OS_LABEL == "win64" and filename.endswith('.zip') and "windows" in filename:
            if re.search(f"^blender-{SEARCH_VER_PATTERN}", filename):
                matching_archives.append(filename)
        elif OS_LABEL == "linux" and filename.endswith('.tar.xz') and "linux" in filename:
            if re.search(f"^blender-{SEARCH_VER_PATTERN}", filename):
                matching_archives.append(filename)
        elif OS_LABEL == "macos" and filename.endswith('.dmg'):
            # Detect macOS architecture matching (Apple Silicon vs Intel)
            if "arm64" in sys_arch.lower() or "apple" in sys_arch.lower():
                if "arm64" in filename.lower() and re.search(f"^blender-{SEARCH_VER_PATTERN}", filename):
                    matching_archives.append(filename)
            else:
                if ("x64" in filename.lower() or "x86_64" in filename.lower()) and re.search(f"^blender-{SEARCH_VER_PATTERN}", filename):
                    matching_archives.append(filename)

    if matching_archives:
        # Natural alphanumeric version sorting (e.g. 5.1.10 > 5.1.2)
        def version_key(v):
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', v)]
        
        matching_archives.sort(key=version_key)
        BLENDER_FILE = matching_archives[-1]
        BLENDER_URL = f"{STABLE_FOLDER_URL}{BLENDER_FILE}"
        SOURCE_TYPE = "stable"
        print(f"Found Stable Release: {BLENDER_FILE}")

# 2. Fallback to builder.blender.org for daily development builds (alpha/beta/rc)
if not BLENDER_FILE:
    print("No stable release found. Checking builder daily archives...")
    DAILY_ARCHIVE_URL = "https://builder.blender.org/download/daily/archive/"
    daily_html = fetch_url(DAILY_ARCHIVE_URL)
    
    if daily_html:
        links = re.findall(r'href="([^"]+)"', daily_html)
        matching_daily = []
        
        for link in links:
            if OS_LABEL == "win64" and link.endswith('.zip') and "windows" in link:
                if re.search(f"blender-{B3DVERSION}[0-9.]*", link):
                    matching_daily.append(link)
            elif OS_LABEL == "linux" and link.endswith('.tar.xz') and "linux" in link:
                if re.search(f"blender-{B3DVERSION}[0-9.]*", link):
                    matching_daily.append(link)
            elif OS_LABEL == "macos" and link.endswith('.dmg') and "macos" in link:
                if "arm64" in sys_arch.lower() or "apple" in sys_arch.lower():
                    if "arm64" in link.lower() and re.search(f"blender-{B3DVERSION}[0-9.]*", link):
                        matching_daily.append(link)
                else:
                    if "x64" in link.lower() and re.search(f"blender-{B3DVERSION}[0-9.]*", link):
                        matching_daily.append(link)
                        
        if matching_daily:
            # Pick the most recent entry from daily archive index (usually bottom of list)
            BLENDER_URL = matching_daily[-1]
            BLENDER_FILE = BLENDER_URL.split('/')[-1]
            SOURCE_TYPE = "daily"
            print(f"Found Builder Daily/Beta Release: {BLENDER_FILE}")

if not BLENDER_FILE:
    print(f"Error: Could not resolve a Blender release matching '{B3DVERSION}' for platform {OS_LABEL}.")
    sys.exit(1)

# Determine Hash
if SOURCE_TYPE == "stable":
    BLENDERHASH = "stable"
else:
    # Extract hash (e.g., blender-5.1.0-beta+v51.0640836baa4e -> 0640836baa4e)
    hash_match = re.search(r'\+v[0-9.]+\.([a-fA-F0-9]+)', BLENDER_FILE)
    if hash_match:
        BLENDERHASH = hash_match.group(1)
    else:
        # Fallback regex hash check
        hash_match = re.search(r'-([a-fA-F0-9]+)-(windows|linux|macos)', BLENDER_FILE)
        BLENDERHASH = hash_match.group(1) if hash_match else "daily"

# Resolve folder name after decompression
if BLENDER_FILE.endswith('.tar.xz'):
    BLENDERLOC = BLENDER_FILE.replace('.tar.xz', '')
elif BLENDER_FILE.endswith('.zip'):
    BLENDERLOC = BLENDER_FILE.replace('.zip', '')
elif BLENDER_FILE.endswith('.dmg'):
    BLENDERLOC = BLENDER_FILE.replace('.dmg', '')

target_extract_path = os.path.join(DOWNLOADS, BLENDERLOC)

# Download and extraction logic
if os.path.exists(target_extract_path):
    print(f"You already have the latest Blender build ({BLENDERHASH}) extracted at: {DOWNLOADWSL}")
else:
    archive_dest = os.path.join(DOWNLOADS, BLENDER_FILE)
    print(f"Downloading {BLENDER_FILE} from {BLENDER_URL}")
    
    # Download with beautiful terminal progress metrics
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    req = urllib.request.Request(BLENDER_URL, headers={'User-Agent': user_agent})
    
    try:
        import ssl
        context = ssl._create_unverified_context()
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
        response = opener.open(req)
    except:
        response = urllib.request.urlopen(req)
        
    with response, open(archive_dest, 'wb') as out_file:
        total_size = int(response.info().get('Content-Length', 0))
        downloaded = 0
        block_size = 1024 * 128
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size:
                percent = (downloaded / total_size) * 100
                sys.stdout.write(f"\rDownloading: {percent:.1f}% ({downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)")
                sys.stdout.flush()
        print()

    # Extract Archive cross-platform
    print("Extracting package...")
    if BLENDER_FILE.endswith('.zip'):
        with zipfile.ZipFile(archive_dest, 'r') as zip_ref:
            zip_ref.extractall(DOWNLOADS)
    elif BLENDER_FILE.endswith('.tar.xz'):
        with tarfile.open(archive_dest, 'r:xz') as tar_ref:
            tar_ref.extractall(DOWNLOADS)
    elif BLENDER_FILE.endswith('.dmg'):
        # macOS specific DMG extraction routine
        temp_mount = "/tmp/blender_dmg_mount"
        os.makedirs(temp_mount, exist_ok=True)
        print("Mounting DMG image on macOS...")
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-mountpoint", temp_mount, archive_dest], check=True)
        try:
            app_src = os.path.join(temp_mount, "Blender.app")
            app_dst = os.path.join(target_extract_path, "Blender.app")
            os.makedirs(target_extract_path, exist_ok=True)
            print("Copying Blender.app to Downloads folder...")
            subprocess.run(["cp", "-R", app_src, app_dst], check=True)
        finally:
            print("Unmounting DMG image...")
            subprocess.run(["hdiutil", "detach", temp_mount], check=True)
            shutil.rmtree(temp_mount, ignore_errors=True)

    # Clean up downloaded archive to save disk space
    try:
        os.remove(archive_dest)
    except:
        pass

# --- Register and link management ---
bin_dir = os.path.expanduser('~/bin') if not sys_platform == "Windows" else os.path.join(os.environ.get('USERPROFILE', ''), 'bin')
os.makedirs(bin_dir, exist_ok=True)

if IS_WSL:
    # Run explorer folder opener if enabled
    if OPEN_FOLDER:
        subprocess.run(["explorer.exe", DOWNLOADWSL], shell=True)
    # Register Blender association inside Windows shell registry
    win_exe_path = os.path.join(DOWNLOADWSL, BLENDERLOC, "blender.exe")
    print(f"Registering Blender with Windows Host: {win_exe_path}")
    subprocess.run(["cmd.exe", "/C", f'"{win_exe_path}" --register'], check=True)
    
    # Create standard WSL Symlink targeting Windows binary
    target_bin = os.path.join(DOWNLOADS, BLENDERLOC, "blender.exe")
    symlink_path = os.path.join(bin_dir, f"blender-{B3DVERSION}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(target_bin, symlink_path)
    print(f"Created symlink: {symlink_path} -> {target_bin}")

elif sys_platform == "Windows":
    if OPEN_FOLDER:
        subprocess.run(["explorer.exe", DOWNLOADWSL], shell=True)
    target_bin = os.path.join(DOWNLOADS, BLENDERLOC, "blender.exe")
    print("Registering Blender shell registry details...")
    subprocess.run([target_bin, "--register"], shell=True)
    
    # Create symlink or Windows Cmd wrapper if symlinks fail (Developer Mode restriction)
    symlink_path = os.path.join(bin_dir, f"blender-{B3DVERSION}")
    try:
        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)
        os.symlink(target_bin, symlink_path)
        print(f"Created symlink: {symlink_path} -> {target_bin}")
    except OSError:
        # Fallback to creating a lightweight CLI command wrapper (.bat)
        bat_wrapper = os.path.join(bin_dir, f"blender-{B3DVERSION}.bat")
        with open(bat_wrapper, 'w', encoding='utf-8') as bat_file:
            bat_file.write(f'@echo off\n"{target_bin}" %*\n')
        print(f"Developer Mode disabled. Fallback wrapper created: {bat_wrapper}")

elif sys_platform == "Darwin":
    if OPEN_FOLDER:
        subprocess.run(["open", DOWNLOADS])
    target_bin = os.path.join(DOWNLOADS, BLENDERLOC, "Blender.app", "Contents", "MacOS", "Blender")
    symlink_path = os.path.join(bin_dir, f"blender-{B3DVERSION}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(target_bin, symlink_path)
    print(f"Created macOS Symlink: {symlink_path} -> {target_bin}")

else:
    # Linux Standard Desktop
    if OPEN_FOLDER:
        subprocess.run(["xdg-open", DOWNLOADS])
    target_bin = os.path.join(DOWNLOADS, BLENDERLOC, "blender")
    symlink_path = os.path.join(bin_dir, f"blender-{B3DVERSION}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(target_bin, symlink_path)
    print(f"Created Symlink: {symlink_path} -> {target_bin}")

# --- Version cleanup logic ---
print("Cleaning up older directories exceeding retention targets...")
# Find all extracted directories inside Downloads matching 'blender-*'
all_dirs = []
for entry in os.scandir(DOWNLOADS):
    if entry.is_dir() and entry.name.startswith("blender-"):
        all_dirs.append(entry)

# Sort directories by modified time (newest first)
all_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

# Keep the top N directories, delete the rest
if len(all_dirs) > KEEP:
    for old_dir in all_dirs[KEEP:]:
        print(f"Removing old version directory: {old_dir.path}")
        shutil.rmtree(old_dir.path, ignore_errors=True)

# --- Clean Broken Symlinks in bin ---
if os.path.exists(bin_dir):
    print("Checking for broken symlinks in ~/bin...")
    for file in os.listdir(bin_dir):
        file_path = os.path.join(bin_dir, file)
        
        # Check standard symlinks
        if os.path.islink(file_path):
            if not os.path.exists(os.readlink(file_path)):
                print(f"Removing broken symlink: {file_path}")
                os.remove(file_path)
                
        # Check custom Windows bat wrappers pointing to non-existent binaries
        elif file.endswith('.bat') and file.startswith('blender-'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Parse path from bat wrapper
                quoted_paths = re.findall(r'"([^"]+)"', content)
                if quoted_paths and not os.path.exists(quoted_paths[0]):
                    print(f"Removing broken bat wrapper: {file_path}")
                    os.remove(file_path)
            except:
                pass