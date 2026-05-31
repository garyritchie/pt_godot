#!/usr/bin/env python3
"""
getgodot.py - Robust Cross-Platform Godot Engine Downloader and Environment Manager
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
import argparse
from pathlib import Path

# --- Configuration & Defaults ---
DEFAULT_KEEP = 2

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
    global _parser
    _parser = argparse.ArgumentParser(
        description="Robust Cross-Platform Godot Engine Downloader and Environment Manager"
    )
    # Collect all positional arguments to handle raw versions or variable assignment syntax
    _parser.add_argument(
        "pos_args",
        nargs="*",
        help="Positional arguments. Can be a raw version (e.g. 4.3) or key=value overrides (e.g. GODOT_VERSION=4.3 KEEP=3).",
        default=[]
    )
    _parser.add_argument(
        "-v", "--version",
        help="Godot version to download (alternative to positional argument).",
        default=None
    )
    _parser.add_argument(
        "-k", "--keep",
        type=int,
        help="Number of versions to keep. Overrides env and config.",
        default=None
    )
    _parser.add_argument(
        "--no-open",
        action="store_true",
        help="Suppress opening the download folder after extraction.",
        default=None
    )
    return _parser.parse_args()

# Parse arguments and load configurations
args = parse_arguments()
config_vars = load_makerc()

# Resolve positional argument parameters/overrides (e.g. GODOT_VERSION=4.4 or KEEP=3)
pos_version = None
pos_keep = None
pos_no_open = None

if args.pos_args:
    for arg in args.pos_args:
        if '=' in arg:
            key, val = arg.split('=', 1)
            key = key.strip().upper()
            val = val.strip().strip('"').strip("'")
            if key in ("GODOT_VERSION", "VERSION", "B3DVERSION"):
                pos_version = val
            elif key == "KEEP":
                try:
                    pos_keep = int(val)
                except ValueError:
                    pass
            elif key in ("NO_OPEN", "B3D_NOOPEN"):
                pos_no_open = val.lower() in ("true", "1", "yes")
        else:
            # If raw string without '=', treat as positional version
            pos_version = arg

# 1. Resolve Godot Version (CLI Explicit -> Positional Override -> Env -> .makerc -> Required)
cli_version = args.version or pos_version
GODOT_VERSION_RAW = cli_version or os.environ.get('GODOT_VERSION') or config_vars.get('GODOT_VERSION')

if not GODOT_VERSION_RAW or re.search(r'\{\{.*?\}\}', GODOT_VERSION_RAW):
    print("Error: No Godot version specified. Set the GODOT_VERSION environment variable or pass a version argument.\n")
    _parser.print_help()
    sys.exit(1)

# 2. Resolve Keep count (CLI Explicit -> Positional Override -> Env -> .makerc -> Default)
cli_keep = args.keep if args.keep is not None else pos_keep
KEEP_val = cli_keep if cli_keep is not None else (os.environ.get('KEEP') or config_vars.get('KEEP'))
KEEP = int(KEEP_val) if KEEP_val is not None else DEFAULT_KEEP

# 3. Resolve No Open flag (CLI Explicit -> Positional Override -> Env -> .makerc -> Default)
if args.no_open is True or pos_no_open is True:
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

def create_windows_shortcut(target_bin, version):
    """Creates a Windows Start Menu shortcut (.lnk) using PowerShell."""
    import subprocess
    
    # Ensure Windows backslashes are used and single quotes are escaped for PowerShell
    target_bin_win = target_bin.replace('/', '\\').replace("'", "''")
    if '\\' in target_bin_win:
        working_dir_win = target_bin_win.rsplit('\\', 1)[0]
    else:
        working_dir_win = os.path.dirname(target_bin_win)
        
    ps_script = f"""
    $appData = $env:APPDATA
    if (-not $appData) {{
        $appData = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::ApplicationData)
    }}
    $shortcutDir = Join-Path $appData "Microsoft\\Windows\\Start Menu\\Programs"
    if (-not (Test-Path $shortcutDir)) {{
        New-Item -ItemType Directory -Force -Path $shortcutDir | Out-Null
    }}
    $shortcutPath = Join-Path $shortcutDir "Godot {version}.lnk"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = '{target_bin_win}'
    $Shortcut.WorkingDirectory = '{working_dir_win}'
    $Shortcut.Save()
    """
    
    cmd = "powershell.exe"
    try:
        subprocess.run(
            [cmd, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Created Windows Start Menu shortcut: Godot {version}")
    except Exception as e:
        print(f"Warning: Failed to create Windows Start Menu shortcut: {e}")

def clean_broken_windows_shortcuts():
    """Cleans up any broken Windows Start Menu shortcuts for Godot."""
    import subprocess
    ps_script = """
    $appData = $env:APPDATA
    if (-not $appData) {
        $appData = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::ApplicationData)
    }
    $shortcutDir = Join-Path $appData "Microsoft\\Windows\\Start Menu\\Programs"
    if (Test-Path $shortcutDir) {
        $WshShell = New-Object -ComObject WScript.Shell
        Get-ChildItem -Path $shortcutDir -Filter "Godot *.lnk" | ForEach-Object {
            $shortcut = $WshShell.CreateShortcut($_.FullName)
            $target = $shortcut.TargetPath
            if ($target -and -not (Test-Path $target)) {
                Write-Output "Removing broken shortcut: $($_.FullName) pointing to $target"
                Remove-Item $_.FullName -Force
            }
        }
    }
    """
    cmd = "powershell.exe"
    try:
        subprocess.run(
            [cmd, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        pass

# --- Platform & Architecture Resolution ---
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
        DOWNLOADS = os.path.join(wsl_profile, 'Downloads', f'GODOT_{GODOT_VERSION_RAW}')
        # Get Windows absolute path for registering
        DOWNLOADWSL = subprocess.check_output(['wslpath', '-w', DOWNLOADS], text=True).strip()
    except Exception as e:
        print(f"Warning: Failed to map WSL paths back to Windows host: {e}")
        DOWNLOADS = os.path.expanduser(f'~/Downloads/GODOT_{GODOT_VERSION_RAW}')
        DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "win64"
    EXPLORER = "explorer.exe"
elif sys_platform == "Windows":
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    DOWNLOADS = os.path.join(user_profile, 'Downloads', f'GODOT_{GODOT_VERSION_RAW}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "win64"
    EXPLORER = "explorer.exe"
elif sys_platform == "Darwin":
    DOWNLOADS = os.path.expanduser(f'~/Downloads/GODOT_{GODOT_VERSION_RAW}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "macos"
    EXPLORER = "open"
else:
    DOWNLOADS = os.path.expanduser(f'~/Downloads/GODOT_{GODOT_VERSION_RAW}')
    DOWNLOADWSL = DOWNLOADS
    OS_LABEL = "linux"
    EXPLORER = "xdg-open"

os.makedirs(DOWNLOADS, exist_ok=True)

# --- Extract Mono Preference & Build Clean Versions ---
if "mono" in GODOT_VERSION_RAW.lower():
    IS_MONO = True
    VERSION_CLEAN = re.sub(r'[-_]?mono', '', GODOT_VERSION_RAW, flags=re.IGNORECASE)
    print("Targeting Mono/.NET version of Godot.")
else:
    IS_MONO = False
    VERSION_CLEAN = GODOT_VERSION_RAW
    print("Targeting Standard version of Godot.")

# Separate clean numeric version (e.g. 4.3) from status (e.g. stable, rc1)
m_numeric = re.match(r'^[0-9.]+', VERSION_CLEAN)
VERSION_NUMERIC = m_numeric.group(0) if m_numeric else VERSION_CLEAN
VERSION_STATUS = VERSION_CLEAN[len(VERSION_NUMERIC):].strip('-_ ')

if not VERSION_STATUS:
    VERSION_STATUS = "stable"

print(f"Cleaned version prefix: {VERSION_NUMERIC} (Status tag: {VERSION_STATUS})")

# --- Fetch Available Versions from Godot Engine Archive ---
print("Fetching available version list from godotengine.org/download/archive/...")
archive_index_html = fetch_url("https://godotengine.org/download/archive/")

if not archive_index_html:
    print("Error: Could not retrieve version list from Godot Engine archive website.")
    sys.exit(1)

# Scrape all unique archive subpages
archive_versions = sorted(list(set(re.findall(r'/download/archive/([a-zA-Z0-9.-]+)/?', archive_index_html))), key=lambda v: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', v)])

# Find the best matching tag
VERSION_TARGET_PATTERN = f"^{VERSION_NUMERIC}.*{VERSION_STATUS}"
matched_tags = [tag for tag in archive_versions if re.match(VERSION_TARGET_PATTERN, tag)]

if not matched_tags:
    # Fallback to just matching numeric prefix
    matched_tags = [tag for tag in archive_versions if tag.startswith(VERSION_NUMERIC)]

if not matched_tags:
    print(f"Error: Could not find any release matching prefix '{VERSION_NUMERIC}' in the Godot download archive.")
    print("Available versions are: " + " ".join(archive_versions))
    sys.exit(1)

RESOLVED_TAG = matched_tags[-1]
print(f"Resolved Version Tag: {RESOLVED_TAG}")
SUBPAGE_URL = f"https://godotengine.org/download/archive/{RESOLVED_TAG}/"

# --- Scrape direct platform links from archive subpage ---
print(f"Scanning {SUBPAGE_URL} for matching platform packages...")
subpage_html = fetch_url(SUBPAGE_URL)

if not subpage_html:
    print("Error: Failed to fetch download assets subpage.")
    sys.exit(1)

# Extract all links containing '.zip'
all_zips = set(re.findall(r'href="([^"]+\.zip[^"]*)"', subpage_html))

GODOT_URL = ""
for link in all_zips:
    # Robust filename parsing: handle standard URLs and parameterized ones
    filename = link.split('/')[-1].lower()
    if '?' in link:
        # Check if it has a 'slug=' parameter which represents the target file
        slug_match = re.search(r'[?&]slug=([^&]+)', link, re.IGNORECASE)
        if slug_match:
            filename = slug_match.group(1).lower()
            # If the link has 'mono' but the slug doesn't, ensure it's represented
            if "mono" in link.lower() and "mono" not in filename:
                filename = "mono_" + filename
        else:
            filename = filename.split('?')[0]
    else:
        filename = filename.split('?')[0]
    
    # Filter out export templates, server, and headless builds
    if "templates" in filename or "server" in filename or "headless" in filename:
        continue
        
    if OS_LABEL == "win64":
        # Match Windows binaries (strictly 64-bit, skip 32-bit/arm32)
        if ("win64" in filename or "x64" in filename or "win" in filename) and "win32" not in filename:
            if IS_MONO and "mono" in filename:
                GODOT_URL = link
                break
            elif not IS_MONO and "mono" not in filename:
                GODOT_URL = link
                break
    elif OS_LABEL == "macos":
        # Match macOS binaries
        if "macos" in filename or "osx" in filename:
            if IS_MONO and "mono" in filename:
                GODOT_URL = link
                break
            elif not IS_MONO and "mono" not in filename:
                GODOT_URL = link
                break
    else:
        # Match Linux binaries depending on architecture
        arch_match = False
        if sys_arch.lower() in ("x86_64", "amd64"):
            if any(term in filename for term in ("x86_64", "amd64", "x11.64", "linux.64", "linux_64")) and \
               not any(term in filename for term in ("arm64", "aarch64", "rv64", "riscv64", "32", "x86_32")):
                arch_match = True
        elif sys_arch.lower() in ("aarch64", "arm64"):
            if "arm64" in filename or "aarch64" in filename:
                arch_match = True
                
        if arch_match and ("linux" in filename or "x11" in filename):
            if IS_MONO and "mono" in filename:
                GODOT_URL = link
                break
            elif not IS_MONO and "mono" not in filename:
                GODOT_URL = link
                break

if not GODOT_URL:
    print(f"Error: Could not locate a matching package for architecture '{sys_arch}' on {OS_LABEL}.")
    sys.exit(1)

# --- Bypassing TuxFamily Limitations via GitHub Releases Rewrite ---
if "tuxfamily.org" in GODOT_URL:
    zip_basename = GODOT_URL.split('/')[-1].split('?')[0]
    if any(pre in RESOLVED_TAG.lower() for pre in ("dev", "beta", "rc")):
        # Pre-releases are hosted on the godot-builds mirror repo
        GODOT_URL = f"https://github.com/godotengine/godot-builds/releases/download/{RESOLVED_TAG}/{zip_basename}"
    else:
        # Stable releases are hosted on the main godot repo
        GODOT_URL = f"https://github.com/godotengine/godot/releases/download/{RESOLVED_TAG}/{zip_basename}"
    print(f"Redirected TuxFamily URL to high-speed GitHub Release: {GODOT_URL}")

# --- Determine Destination Filename and Package Labels ---
if "slug=" in GODOT_URL:
    slug_match = re.search(r'slug=([^&]+)', GODOT_URL)
    ver_match = re.search(r'version=([^&]+)', GODOT_URL)
    flav_match = re.search(r'flavor=([^&]+)', GODOT_URL)
    
    slug_val = slug_match.group(1) if slug_match else ""
    ver_val = ver_match.group(1) if ver_match else ""
    flav_val = flav_match.group(1) if flav_match else ""
    
    if "godot" in slug_val.lower():
        GODOT_ZIP = slug_val
    else:
        GODOT_ZIP = f"Godot_v{ver_val}-{flav_val}_{slug_val}"
else:
    GODOT_ZIP = GODOT_URL.split('/')[-1].split('?')[0]

GODOTLOC = GODOT_ZIP.replace('.zip', '')
target_extract_path = os.path.join(DOWNLOADS, GODOTLOC)

# Ensure downloads directory is ready
os.makedirs(DOWNLOADS, exist_ok=True)

# Find out if we already have the target file
CHECK_PATH = ""
if IS_MONO:
    CHECK_PATH = os.path.join(DOWNLOADS, GODOTLOC)
else:
    # Look for matching standard binaries already extracted
    for file in os.listdir(DOWNLOADS):
        if file.startswith(GODOTLOC) and not file.endswith('.zip') and not file.endswith('.log'):
            CHECK_PATH = os.path.join(DOWNLOADS, file)
            break

if CHECK_PATH and os.path.exists(CHECK_PATH):
    print(f"You already have the latest Godot build ({GODOTLOC}) extracted at: {DOWNLOADWSL}")
    if IS_MONO:
        if sys_platform == "Windows" or IS_WSL:
            executable_candidates = list(Path(CHECK_PATH).rglob("*.exe"))
        else:
            executable_candidates = [p for p in Path(CHECK_PATH).rglob("*") if p.is_file() and not p.name.endswith(".dll") and not "godotsharp" in str(p).lower()]
        GODOT_BIN_PATH = str(executable_candidates[0]) if executable_candidates else ""
    else:
        GODOT_BIN_PATH = CHECK_PATH
else:
    archive_dest = os.path.join(DOWNLOADS, GODOT_ZIP)
    print(f"Downloading {GODOT_ZIP} from {GODOT_URL}...")
    
    # Download with beautiful terminal progress metrics
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    req = urllib.request.Request(GODOT_URL, headers={'User-Agent': user_agent})
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

    # Extract Archive cross-platform cleanly inside GODOTLOC directory
    print("Extracting package...")
    extraction_target_dir = os.path.join(DOWNLOADS, GODOTLOC) if IS_MONO else DOWNLOADS
    os.makedirs(extraction_target_dir, exist_ok=True)
    
    with zipfile.ZipFile(archive_dest, 'r') as zip_ref:
        zip_ref.extractall(extraction_target_dir)

    # Clean up ZIP download to save disk space
    try:
        os.remove(archive_dest)
    except:
        pass

    # Resolve target binary dynamically
    if IS_MONO:
        if sys_platform == "Windows" or IS_WSL:
            executable_candidates = list(Path(extraction_target_dir).rglob("*.exe"))
        else:
            executable_candidates = [p for p in Path(extraction_target_dir).rglob("*") if p.is_file() and not p.name.endswith(".dll") and not "godotsharp" in str(p).lower()]
        GODOT_BIN_PATH = str(executable_candidates[0]) if executable_candidates else ""
    else:
        # Standard Standard Godot extracts directly into DOWNLOADS as file
        resolved_filename = ""
        for file in os.listdir(DOWNLOADS):
            if file.startswith(GODOTLOC) and not file.endswith('.zip') and not file.endswith('.log'):
                resolved_filename = file
                break
        GODOT_BIN_PATH = os.path.join(DOWNLOADS, resolved_filename)

if not GODOT_BIN_PATH or not os.path.exists(GODOT_BIN_PATH):
    print("Error: Could not locate the extracted Godot binary in downloads directory.")
    sys.exit(1)

# Ensure execution flags are set on Unix systems
if sys_platform != "Windows":
    try:
        os.chmod(GODOT_BIN_PATH, 0o755)
    except Exception as e:
        print(f"Warning: Failed to set executable permissions: {e}")

print(f"Target binary located at: {GODOT_BIN_PATH}")

# --- Register and link management ---
bin_dir = os.path.expanduser('~/bin') if not sys_platform == "Windows" else os.path.join(os.environ.get('USERPROFILE', ''), 'bin')
os.makedirs(bin_dir, exist_ok=True)

if IS_WSL:
    if OPEN_FOLDER:
        subprocess.run(["explorer.exe", DOWNLOADWSL], shell=True)
    symlink_path = os.path.join(bin_dir, f"godot-{GODOT_VERSION_RAW}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(GODOT_BIN_PATH, symlink_path)
    print(f"Created WSL Symlink: {symlink_path} -> {GODOT_BIN_PATH}")
    
    # Create Windows Start Menu shortcut
    try:
        win_exe_path = subprocess.check_output(['wslpath', '-w', GODOT_BIN_PATH], text=True).strip()
        create_windows_shortcut(win_exe_path, GODOT_VERSION_RAW)
    except Exception as e:
        print(f"Warning: Failed to convert WSL path to Windows path for shortcut: {e}")

elif sys_platform == "Windows":
    if OPEN_FOLDER:
        subprocess.run(["explorer.exe", DOWNLOADWSL], shell=True)
    symlink_path = os.path.join(bin_dir, f"godot-{GODOT_VERSION_RAW}")
    try:
        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)
        os.symlink(GODOT_BIN_PATH, symlink_path)
        print(f"Created symlink: {symlink_path} -> {GODOT_BIN_PATH}")
    except OSError:
        # Fallback to creating a lightweight CLI command wrapper (.bat)
        bat_wrapper = os.path.join(bin_dir, f"godot-{GODOT_VERSION_RAW}.bat")
        with open(bat_wrapper, 'w', encoding='utf-8') as bat_file:
            bat_file.write(f'@echo off\n"{GODOT_BIN_PATH}" %*\n')
        print(f"Developer Mode disabled. Fallback wrapper created: {bat_wrapper}")
        
    # Create Windows Start Menu shortcut
    create_windows_shortcut(GODOT_BIN_PATH, GODOT_VERSION_RAW)

elif sys_platform == "Darwin":
    if OPEN_FOLDER:
        subprocess.run(["open", DOWNLOADS])
    # macOS Godot extracted can be standard Godot.app -> link the internal executable
    if GODOT_BIN_PATH.endswith(".app"):
        target_bin = os.path.join(GODOT_BIN_PATH, "Contents", "MacOS", "Godot")
    else:
        target_bin = GODOT_BIN_PATH
        
    symlink_path = os.path.join(bin_dir, f"godot-{GODOT_VERSION_RAW}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(target_bin, symlink_path)
    print(f"Created macOS Symlink: {symlink_path} -> {target_bin}")

else:
    # Linux Standard Desktop
    if OPEN_FOLDER:
        subprocess.run(["xdg-open", DOWNLOADS])
    symlink_path = os.path.join(bin_dir, f"godot-{GODOT_VERSION_RAW}")
    if os.path.exists(symlink_path) or os.path.islink(symlink_path):
        os.remove(symlink_path)
    os.symlink(GODOT_BIN_PATH, symlink_path)
    print(f"Created Symlink: {symlink_path} -> {GODOT_BIN_PATH}")

# --- Version cleanup logic ---
print("Cleaning up older directories exceeding retention targets...")
# Find all extracted directories/files inside Downloads matching 'Godot_v*'
all_packages = []
for entry in os.scandir(DOWNLOADS):
    # Match directories (e.g. Mono folders) or standard standalone binaries
    if entry.name.startswith("Godot_v") and not entry.name.endswith(".zip") and not entry.name.endswith(".log"):
        all_packages.append(entry)

# Sort packages by modified time (newest first)
all_packages.sort(key=lambda x: x.stat().st_mtime, reverse=True)

# Keep the top N packages, delete the rest
if len(all_packages) > KEEP:
    for old_pkg in all_packages[KEEP:]:
        print(f"Removing old version package: {old_pkg.path}")
        if old_pkg.is_dir():
            shutil.rmtree(old_pkg.path, ignore_errors=True)
        else:
            try:
                os.remove(old_pkg.path)
            except:
                pass

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
        elif file.endswith('.bat') and file.startswith('godot-'):
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

# --- Clean Windows Start Menu shortcuts ---
if sys_platform == "Windows" or IS_WSL:
    print("Checking for broken Windows Start Menu shortcuts...")
    clean_broken_windows_shortcuts()