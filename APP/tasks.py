#!/usr/bin/env python3
"""
tasks.py - Universal Cross-Platform Task Runner and Project Orchestrator
Replaces legacy Makefile dependencies with robust, native, dependency-free Python.
"""

import os
import sys
import re
import shutil
import platform
import subprocess
import zipfile
import fnmatch
from datetime import datetime
from pathlib import Path

# --- ANSI Terminal Colors ---
class Colors:
    GREEN = '\033[32m' if sys.platform != 'win32' or os.getenv('COLORTERM') else ''
    YELLOW = '\033[33m' if sys.platform != 'win32' or os.getenv('COLORTERM') else ''
    WHITE = '\033[37m' if sys.platform != 'win32' or os.getenv('COLORTERM') else ''
    RESET = '\033[0m' if sys.platform != 'win32' or os.getenv('COLORTERM') else ''

# --- Configuration & Environment Loader ---
def load_config():
    """Parses local and parent configurations (.makerc, .env) on startup."""
    config = {}
    for rc_path in ['.makerc', '../.makerc', '.env', '../.env']:
        if os.path.exists(rc_path):
            try:
                with open(rc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, val = line.split('=', 1)
                            config[key.strip()] = val.strip().strip('"').strip("'").strip()
            except Exception as e:
                print(f"Warning: Failed to parse configuration {rc_path}: {e}")
    return config

# Parse dynamic key=value command-line argument overrides (e.g. FOLDER=RENDER/ or CHANGES=yes)
cli_config = {}
clean_args = []
for arg in sys.argv[1:]:
    if '=' in arg:
        k, v = arg.split('=', 1)
        cli_config[k.strip().upper()] = v.strip().strip('"').strip("'")
    else:
        clean_args.append(arg)

# Merge loaders (CLI arguments take absolute precedence over environment files)
config = load_config()
for k, v in cli_config.items():
    config[k] = v

# Set global configurations
PROJECT = config.get('PROJECT', 'default_project')
PREFIX = config.get('PREFIX', PROJECT.replace('/', '_').lower())
WIP = config.get('WIP', 'RENDER/ SCRIPT/').split()
KEEP = int(config.get('KEEP', 2))
B3DVERSION = config.get('B3DVERSION', '5.1')
GODOT_VERSION = config.get('GODOT_VERSION', '4.3')
DEPLOYFILES = config.get('DEPLOYFILES', 'DAILIES')
BUILDDIR = config.get('BUILDDIR', 'BUILD')
DISTDIR = config.get('DISTDIR', 'DIST')

# --- Helper Functions ---
def get_git_info():
    """Gets current git branch and short commit hash securely."""
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
        if branch in ("main", "master"):
            try:
                branch = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0'], text=True).strip()
            except:
                pass
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
        return branch, commit
    except Exception:
        return "main", "unknown"

def read_gitignore():
    """Parses local .gitignore file into search exclusion patterns."""
    patterns = ['.git', 'node_modules', '__pycache__', '.DS_Store', 'Thumbs.db', 'DIST']
    if os.path.exists('.gitignore'):
        try:
            with open('.gitignore', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line.rstrip('/'))
        except:
            pass
    return patterns

def is_ignored(path, patterns):
    """Evaluates if a path matches typical or git-defined exclusion patterns."""
    path_parts = Path(path).parts
    for part in path_parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern) or part == pattern:
                return True
    return False

def get_magick_cmd():
    """Detects correct system command call configuration for ImageMagick."""
    if shutil.which("magick"):
        return ["magick"]
    elif shutil.which("convert"):
        return ["convert"]
    return None

def get_mogrify_cmd():
    """Detects correct system command call configuration for ImageMagick Mogrify."""
    if shutil.which("magick"):
        return ["magick", "mogrify"]
    elif shutil.which("mogrify"):
        return ["mogrify"]
    return None

# --- Task Registry Decorator ---
TASKS = {}

def task(category="options", name=None):
    """Decorator to register functions as executable task targets."""
    def decorator(func):
        task_name = name or func.__name__.replace('_', '-')
        TASKS[task_name] = {
            'func': func,
            'category': category,
            'desc': func.__doc__.splitlines()[0].strip() if func.__doc__ else 'No description provided.'
        }
        return func
    return decorator

# --- PROJECT CATEGORY TASKS ---

@task(category="project", name="client-info")
def client_info():
    """Collect client overrides and makerc configurations into a single file.

    Extracts variables and environment blocks from active configurations (.makerc, .env)
    and aggregates them inside local file .client.info to preserve environment overrides.
    """
    print("Collecting client override metrics into .client.info...")
    lines = []
    for filepath in ['.makerc', '../.makerc', '.env', '../.env']:
        if os.path.exists(filepath):
            lines.append(f"# {filepath}\n")
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines.append(f.read())
            except Exception as e:
                print(f"Warning: Failed to read {filepath}: {e}")
            lines.append("\n")
            
    with open(".client.info", "w", encoding="utf-8") as out:
        out.writelines(lines)
    print("Successfully compiled .client.info")

@task(category="project")
def put_clientinfo():
    """Create defaults to use with projects (portability). Splits consolidated details.

    Reads variables stored inside local file .client.info and splits the details
    back out to restore override properties inside parent-level configuration profiles
    (.makerc and .env).
    """
    client_info_path = ".client.info"
    if not os.path.exists(client_info_path):
        print(f"Error: {client_info_path} does not exist. Run generation steps first.")
        return
    
    print(f"Restoring environment overrides from {client_info_path}...")
    try:
        with open(client_info_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = content.split('# ../')
        for section in sections:
            if not section.strip():
                continue
            lines = section.splitlines()
            target_file = lines[0].strip()
            file_data = "\n".join(lines[1:])
            
            target_path = Path("..") / target_file
            with open(target_path, 'w', encoding='utf-8') as out_f:
                out_f.write(file_data.strip() + "\n")
            print(f"Restored file: {target_path}")
    except Exception as e:
        print(f"Error executing put-clientinfo split: {e}")

@task(category="project")
def todo():
    """Consolidates ToDo lists from readme.md and readme.adoc files in parent folder.

    Recursively scans markdown/asciidoc documentation structures inside sibling/parent project folders
    and compiles a consolidated ledger of pending todo items inside parent directory path: ../todo.md
    """
    output_path = Path("../todo.md")
    print(f"Scanning parent directories for TODO lists -> writing to {output_path}...")
    
    todo_lines = ["## Todo\n\n"]
    ignore_patterns = read_gitignore()
    
    for path in Path("..").rglob("*"):
        if is_ignored(path, ignore_patterns):
            continue
        if path.is_file() and path.name.lower() in ("readme.md", "readme.adoc"):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines):
                    if re.match(r'^(#|=)+\s*todo', line, re.IGNORECASE):
                        rel_path = os.path.relpath(path, start=".")
                        todo_lines.append(f"### [[{rel_path}]]\n\n")
                        for j in range(1, 6):
                            if i + j < len(lines):
                                todo_lines.append(lines[i + j])
                        todo_lines.append("\n\n")
                        break
            except Exception as e:
                print(f"Skipping {path}: {e}")
                
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(todo_lines)
        print("Todo report compiled successfully.")
    except Exception as e:
        print(f"Error compiling Todo report: {e}")

@task(category="project")
def list_closed():
    """List projects that have had closedown activities recorded in closedown.md.

    Scans parent directories recursively for completed closedown logs (where items are checked off)
    and aggregates matching paths inside parent directory file: ../closed.md
    """
    output_path = Path("../closed.md")
    print(f"Scanning parent directories for closed tasks -> writing to {output_path}...")
    
    closed_lines = ["## Closed Projects\n\n"]
    ignore_patterns = read_gitignore()
    
    for path in Path("..").rglob("closedown.md"):
        if is_ignored(path, ignore_patterns):
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if re.search(r'-\s*\[x\]', content, re.IGNORECASE):
                rel_path = os.path.relpath(path, start=".")
                closed_lines.append(f"- [[{rel_path}]]\n")
        except Exception as e:
            print(f"Skipping {path}: {e}")
            
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(closed_lines)
        print("Closed projects report compiled.")
    except Exception as e:
        print(f"Error compiling closed projects report: {e}")

@task(category="project")
def list_notclosed():
    """List projects that have not had closedown activities completed.

    Scans parent directories recursively for active closedown.md check-sheets containing unchecked entries
    and compiles tracking links into parent directory path: ../notclosed.md
    """
    output_path = Path("../notclosed.md")
    print(f"Scanning parent directories for active closedown targets -> writing to {output_path}...")
    
    not_closed_lines = ["## Not Closed\n\n"]
    ignore_patterns = read_gitignore()
    
    for path in Path("..").rglob("closedown.md"):
        if is_ignored(path, ignore_patterns):
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if re.search(r'-\s*\[\s*\]', content):
                rel_path = os.path.relpath(path, start=".")
                not_closed_lines.append(f"- [[{rel_path}]]\n")
        except Exception as e:
            print(f"Skipping {path}: {e}")
            
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(not_closed_lines)
        print("Uncompleted projects report compiled.")
    except Exception as e:
        print(f"Error compiling active projects report: {e}")

@task(category="project")
def list_archived():
    """Lists archived projects by identifying '# archived' flags inside readmes.

    Recursively scans parent project directories for documentation files containing an Archived header block
    and compiles a list of matches in path: ../archived.md
    """
    output_path = Path("../archived.md")
    print(f"Scanning parent directories for archived markers -> writing to {output_path}...")
    
    archived_lines = ["## Archived\n\n"]
    ignore_patterns = read_gitignore()
    
    for path in Path("..").rglob("*"):
        if is_ignored(path, ignore_patterns):
            continue
        if path.is_file() and path.name.lower() in ("readme.md", "readme.adoc"):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if re.search(r'^(#|=)+\s*archived', content, re.MULTILINE | re.IGNORECASE):
                    rel_path = os.path.relpath(path, start=".")
                    archived_lines.append(f"- [[{rel_path}]]\n")
            except Exception as e:
                print(f"Skipping {path}: {e}")
                
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(archived_lines)
        print("Archived projects report compiled.")
    except Exception as e:
        print(f"Error compiling archived report: {e}")

@task(category="project")
def reports():
    """WIP: Generate collective reports on Todo, Not|Closed, and Archived status.

    Runs sequentially: todo, list-closed, list-notclosed, and list-archived to compile
    a complete state report in parent directory files.
    """
    todo()
    list_closed()
    list_notclosed()
    list_archived()

@task(category="project")
def simplify():
    """Remove unused folders recursively (customizable target via FOLDER=path).

    Cleans unused and non-essential directories from the active workspace layout.
    By default, preserves protected directories (such as scene, model, texture, app, doc).

    Configuration Options:
      FOLDER        Local path of target subdirectory to selectively delete.
                    Example: FOLDER=RENDER/ python tasks.py simplify
                    If omitted, runs full top-level cleanups preserving standard project lanes.
    """
    target_pattern = config.get('FOLDER', '**/')
    print(f"Beginning layout simplification. Sweeping folder pattern: {target_pattern}")
    
    protected_folders = [w.lower().rstrip('/') for w in WIP] + ['app', 'scene', 'model', 'doc', 'texture', 'build', 'dist']
    
    if target_pattern == "**/":
        for path in Path(".").iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                if path.name.lower() not in protected_folders:
                    print(f"Removing unused directory: {path}")
                    shutil.rmtree(path, ignore_errors=True)
    else:
        target_path = Path(target_pattern)
        if target_path.exists() and target_path.is_dir():
            print(f"Removing targeted directory: {target_path}")
            shutil.rmtree(target_path, ignore_errors=True)
    print("Project layout simplification complete.")

@task(category="project")
def setup():
    """Perform initial configuration setup by running config.sh script.

    Verifies the existence of local initialization file config.sh and launches it
    to complete automated configuration routines and baseline checks.
    """
    setup_file = "config.sh"
    if not os.path.exists(setup_file):
        print("Setup has already been performed and configuration script is unavailable.")
    else:
        print("Executing configuration script...")
        subprocess.run(["bash", setup_file], check=True)

@task(category="project")
def doc():
    """Compile documentation details listing and folder mapping indexes.

    Generates DOC/folderdetails.md recursively by extracting folder layout details,
    cross-referencing with active gitignore patterns, and appending ignored assets.
    """
    print("Generating documentation metadata files...")
    ignored_out = Path(".gitkeep_ignored.md")
    
    ignored_lines = ["## Ignored Folders\n\nThe contents of the following folders are not tracked/synchronized using Git/Syncthing:\n\n```\n"]
    
    # Mirroring legacy grep filter on .gitignore files
    for filepath in ['.gitignore', '../.gitignore']:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ignored_lines.append(f"{line}\n")
            except:
                pass
                
    ignored_lines.append("```\n\n")
    with open(ignored_out, "w", encoding="utf-8") as f:
        f.writelines(ignored_lines)
        
    # Aggregate compiled documentation file
    doc_out = Path("DOC/folderdetails.md")
    doc_out.parent.mkdir(parents=True, exist_ok=True)
    
    combined_lines = []
    for doc_src in ['.gitkeep.md', str(ignored_out)]:
        if os.path.exists(doc_src):
            try:
                with open(doc_src, 'r', encoding='utf-8') as f:
                    combined_lines.append(f.read())
                    combined_lines.append("\n")
            except:
                pass
                
    with open(doc_out, "w", encoding="utf-8") as f:
        f.writelines(combined_lines)
        
    # Cleanup temporary compile blocks
    if ignored_out.exists():
        os.remove(ignored_out)
    print(f"Documentation compiled successfully inside {doc_out}")

@task(category="project")
def archive():
    """Archive project for coldstorage (removes git history, respects .gitignore, packages to ZIP).

    Compresses the active workspace into a highly-compressed .zip deliverable, keeping
    it clean of temporary runtime caches or ignored assets by strictly adhering to gitignore guidelines.
    Targets folder path: ../ARCHIVE/ with filename formatted using git tracking commit metrics.
    """
    branch, commit = get_git_info()
    archive_name = f"{PREFIX}_{commit}.zip"
    
    # Resolve the partition level ARCHIVE path
    archive_dir = Path("../ARCHIVE")
    archive_dir.mkdir(parents=True, exist_ok=True)
    target_zip_path = archive_dir / archive_name
    
    print(f"Creating clean production archive at: {target_zip_path}...")
    ignore_patterns = read_gitignore()
    
    try:
        with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('.'):
                dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), ignore_patterns)]
                for file in files:
                    file_path = os.path.join(root, file)
                    if not is_ignored(file_path, ignore_patterns):
                        archive_subpath = os.path.join(PROJECT, os.path.relpath(file_path, '.'))
                        zipf.write(file_path, archive_subpath)
                        
        print(f"Production Archive packaged successfully: {target_zip_path}")
        
        readme_path = Path("readme.md")
        if readme_path.exists():
            entry = f"\n\n## Archived\n\n```\n{target_zip_path.resolve()}\n```\n\n"
            with open(readme_path, 'a', encoding='utf-8') as f:
                f.write(entry)
            print("Archived tracking metrics updated in local readme.md")
    except Exception as e:
        print(f"Error executing project archive steps: {e}")

# --- TRANSMIT CATEGORY TASKS ---

@task(category="transmit")
def stage():
    """Deploy DEPLOYFILES contents for review on staging server.

    Pushes build deliverables asynchronously to remote review repositories using rsync.

    Configuration Options:
      DEPLOYFILES   Directory target to deploy (default: DAILIES).
      REMOTESTAGE   Staging server remote path (e.g. host:/var/www/html).
      PROJECT       Relative destination subfolder.
      RSYNC_OPTS    Override parameters passed directly downstream to rsync.
    """
    deploy_target = config.get('DEPLOYFILES', 'DAILIES')
    remote_stage = config.get('REMOTESTAGE', '')
    project = config.get('PROJECT', '')
    
    if not remote_stage or not project:
        print("Error: REMOTESTAGE or PROJECT target not defined.")
        return
        
    stage_host = remote_stage.split(':')[0] if ':' in remote_stage else remote_stage
    stage_path = remote_stage.split(':')[1] if ':' in remote_stage else ''
    
    # Create remote folder
    print(f"Preparing staging directories: ssh {stage_host} mkdir -p {stage_path}/{project}")
    subprocess.run(["ssh", stage_host, f"mkdir -p {stage_path}/{project}"])
    
    branch, commit = get_git_info()
    
    exclude_file = Path(deploy_target) / "exclude.txt"
    exclude_args = ["--exclude-from", str(exclude_file)] if exclude_file.exists() else []
    rsync_opts = config.get('RSYNC_OPTS', '--copy-links').split()
    
    if deploy_target == "DAILIES":
        cmd = ["rsync", "-azvh"] + exclude_args + ["--stats", "--progress", "--delete", "DAILIES/", f"{stage_host}:{stage_path}/{project}/DAILIES/"]
    else:
        cmd = ["rsync", "-azvh"] + exclude_args + rsync_opts + ["--stats", "--progress", f"{deploy_target}/", f"{stage_host}:{stage_path}/{project}/{branch}/"]
        
    print(f"Running Staging deployment: {' '.join(cmd)}")
    subprocess.run(cmd)

@task(category="transmit")
def deploy():
    """Deploy tested, stable deliverables to target production servers.

    Performs a production-grade deployment synchronization of specified files.

    Configuration Options:
      DEPLOYFILES   Source target directory folder (default: DEPLOY).
      REMOTEDEPLOY  Target server endpoint (e.g. host:/var/www/html/live).
    """
    deploy_target = config.get('DEPLOYFILES', 'DEPLOY')
    remote_deploy = config.get('REMOTEDEPLOY', '')
    
    if not remote_deploy:
        print("Error: REMOTEDEPLOY server endpoint configuration missing.")
        return
        
    exclude_file = Path(deploy_target) / "exclude.txt"
    exclude_args = ["--exclude-from", str(exclude_file)] if exclude_file.exists() else []
    
    cmd = ["rsync", "-azvh"] + exclude_args + ["--stats", "--progress", f"{deploy_target}/", remote_deploy]
    print(f"Executing production deployment: {' '.join(cmd)}")
    subprocess.run(cmd)

@task(category="transmit")
def clean():
    """Cleans remote staging directories, or removes older local BUILDFILES.

    Clears staging target locations or manages retention on build folders.

    Configuration Options:
      TARGET        Must be set to 'stage' to trigger remote staging server cleanups.
      BUILDFILES    Files matching pattern to scan and perform local retention sweeping.
    """
    target = config.get('TARGET', '')
    build_pattern = config.get('BUILDFILES', '')
    
    if target == "stage":
        remote_stage = config.get('REMOTESTAGE', '')
        project = config.get('PROJECT', '')
        if remote_stage and project:
            stage_host = remote_stage.split(':')[0] if ':' in remote_stage else remote_stage
            stage_path = remote_stage.split(':')[1] if ':' in remote_stage else ''
            remote_cmd = f"rm -rf {stage_path}/{project}/*"
            print(f"Cleaning remote staging directory: ssh {stage_host} '{remote_cmd}'")
            subprocess.run(["ssh", stage_host, remote_cmd])
    else:
        print("No TARGET=stage parameter detected. Skipping staging cleanup.")
        
    if not build_pattern:
        print("BUILDFILES not defined; skipping local directory cleanup.")
    else:
        print(f"Scanning target pattern: {build_pattern}")
        matched_paths = sorted(Path(".").glob(build_pattern), key=os.path.getmtime, reverse=True)
        if len(matched_paths) > 1:
            # Keep newest file, trash older items
            for old_path in matched_paths[1:]:
                print(f"Moving {old_path} to system Trash...")
                try:
                    import send2trash
                    send2trash.send2trash(str(old_path))
                except:
                    if old_path.is_dir():
                        shutil.rmtree(old_path, ignore_errors=True)
                    else:
                        os.remove(old_path)

@task(category="transmit")
def package():
    """Package compiled build folders to 7z/zip distributions, auto-building logs.

    Compiles, documents, and compresses build folders for deployment.

    Configuration Options:
      CHANGES        Set to 'yes' to auto-generate changes.md from Git commit logs (default: no).
      BUILDFILES     Target workspace source folder (default: BUILD).
      PACKAGEFORMAT  Compression file format, '7z' or 'zip' (default: 7z).
      SUFFIX         Custom suffix appended to output name.
      UPLOAD         Set to 'stage' to upload the archive directly via rsync after generation.
    """
    changes = config.get('CHANGES', 'no')
    build_dir = config.get('BUILDFILES', 'BUILD')
    package_format = config.get('PACKAGEFORMAT', '7z')
    suffix = config.get('SUFFIX', '')
    upload = config.get('UPLOAD', 'stage')
    
    branch, commit = get_git_info()
    today = datetime.now().strftime('%Y-%m-%d')
    
    if changes.lower() == "yes":
        os.makedirs(build_dir, exist_ok=True)
        # Write packaging build parameters
        with open(f"{build_dir}/version.txt", "w", encoding="utf-8") as f:
            f.write(f"{branch} {commit}\n")
            
        print("Querying Git logs to compile changes.md changes ledger...")
        try:
            log_output = subprocess.check_output([
                'git', 'log', f'--after={today}-00:00', f'--before={today}-23:59',
                '--pretty=format:- %s (%h)'
            ], text=True).strip()
        except:
            log_output = "- General stability updates."
            
        with open(f"{build_dir}/changes.md", "w", encoding="utf-8") as f:
            f.write(f"## {today}\n\n{log_output}\n")
            
    build_name = f"{PREFIX}_{branch}_{commit}{suffix}.{package_format}"
    os.makedirs("DIST", exist_ok=True)
    dist_path = f"DIST/{build_name}"
    
    print(f"Creating packed archive: {dist_path}...")
    if package_format == "zip":
        zip_includes = []
        if os.path.exists("package.txt"):
            with open("package.txt", "r", encoding="utf-8") as f:
                zip_includes = [line.strip() for line in f if line.strip()]
                
        exclude_patterns = []
        exclude_file = Path(DEPLOYFILES) / "exclude.txt"
        if exclude_file.exists():
            with open(exclude_file, "r", encoding="utf-8") as f:
                exclude_patterns = [line.strip() for line in f if line.strip()]
                
        with zipfile.ZipFile(dist_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    fpath = os.path.join(root, file)
                    if any(fnmatch.fnmatch(file, p) for p in exclude_patterns):
                        continue
                    zipf.write(fpath, os.path.relpath(fpath, '.'))
            for item in zip_includes:
                if os.path.exists(item):
                    if os.path.isdir(item):
                        for root, _, files in os.walk(item):
                            for f in files:
                                fpath = os.path.join(root, f)
                                zipf.write(fpath, os.path.relpath(fpath, '.'))
                    else:
                        zipf.write(item, item)
    else:
        # Standard 7z compression routing
        if shutil.which("7z"):
            subprocess.run(["7z", "a", f"-t{package_format}", dist_path, build_dir])
        else:
            print("Fallback: 7z CLI not installed. packaging natively as .zip")
            fallback_zip = dist_path.replace(f".{package_format}", ".zip")
            with zipfile.ZipFile(fallback_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(build_dir):
                    for file in files:
                        fpath = os.path.join(root, file)
                        zipf.write(fpath, os.path.relpath(fpath, '.'))
                        
    if upload == "stage":
        remote_stage = config.get('REMOTESTAGE', '')
        project = config.get('PROJECT', '')
        if remote_stage and project:
            cmd = ["rsync", "-av", "--partial", "--inplace", "--progress", dist_path, f"{remote_stage}/{project}/{build_name}"]
            print(f"Uploading packaged build assets: {' '.join(cmd)}")
            subprocess.run(cmd)

# --- IMAGE CATEGORY TASKS ---

@task(category="image", name="packed-maps")
def packed_maps():
    """Pack displacement/roughness channels into multi-channel normal/albedo texture maps.

    Recursively scans the TEXTURE directory for *Normal.jpg and *Albedo.jpg texture maps,
    identifies matching Displacement and Roughness maps, and packs their channels natively
    into consolidated transparent outputs (*Normal-Displacement.png, *Albedo-Roughness.png).
    Requires ImageMagick.
    """
    magick = get_magick_cmd()
    if not magick:
        print("Error: ImageMagick (convert/magick) is required to pack texture channels.")
        return
        
    normal_maps = list(Path("TEXTURE").rglob("*_Normal.jpg"))
    albedo_maps = list(Path("TEXTURE").rglob("*_Albedo.jpg"))
    
    for normal in normal_maps:
        disp = Path(str(normal).replace("_Normal.jpg", "_Displacement.jpg"))
        output = Path(str(normal).replace("_Normal.jpg", "_Normal-Displacement.png"))
        if disp.exists():
            print(f"Combining {normal.name} and {disp.name} into consolidated displacement normal...")
            subprocess.run(magick + [str(normal), str(disp), "-compose", "CopyOpacity", "-composite", str(output)])
            
    for albedo in albedo_maps:
        rough = Path(str(albedo).replace("_Albedo.jpg", "_Roughness.jpg"))
        output = Path(str(albedo).replace("_Albedo.jpg", "_Albedo-Roughness.png"))
        if rough.exists():
            print(f"Combining {albedo.name} and {rough.name} into consolidated albedo roughness...")
            subprocess.run(magick + [str(albedo), str(rough), "-compose", "CopyOpacity", "-composite", str(output)])

@task(category="image")
def metalness():
    """Make a metalness map from gloss map (GLOSS=y default).

    Generates Unity-compliant metallic-smoothness maps from individual gloss targets
    located inside the TEXTURE directory. Requires ImageMagick.

    Configuration Options:
      GLOSS         Set to 'y' (default) to negate channels and generate inverted smoothness.
    """
    gloss = config.get('GLOSS', 'y')
    magick = get_magick_cmd()
    if not magick:
        print("Error: ImageMagick is required to build metalness texture channels.")
        return
        
    for gloss_map in Path("TEXTURE").rglob("*_g.png"):
        output = Path(str(gloss_map).replace("_g.png", "_metalness.png"))
        print(f"Constructing metalness map channel targeting {output.name}...")
        
        temp_file = "temp_metal.png"
        shutil.copy2(gloss_map, temp_file)
        
        if gloss.lower() == "y":
            cmd = magick + [
                temp_file, "-channel", "rgba", "-alpha", "on", "-separate", "-swap", "0,3", "-combine",
                "-channel", "R", "-evaluate", "set", "0%", "+channel",
                "-channel", "B,G", "-evaluate", "set", "100%", "+channel",
                "-channel", "A", "-negate", "+channel", "-colorspace", "sRGB", str(output)
            ]
        else:
            cmd = magick + [
                temp_file, "-channel", "rgba", "-alpha", "on", "-separate", "-swap", "0,3", "-combine",
                "-channel", "R", "-evaluate", "set", "0%", "+channel",
                "-channel", "B,G", "-evaluate", "set", "100%", "+channel", "-colorspace", "sRGB", str(output)
            ]
        subprocess.run(cmd)
        if os.path.exists(temp_file):
            os.remove(temp_file)

@task(category="image")
def orm():
    """Make a glTF-compliant Occlusion-Roughness-Metallic map from individual texture files.

    Packs distinct Ambient Occlusion, Roughness, and Metallic textures into a unified,
    optimized glTF-compliant ORM texture file (Red: AO, Green: Roughness, Blue: Metalness).
    Requires ImageMagick.
    """
    magick = get_magick_cmd()
    if not magick:
        print("Error: ImageMagick is required to pack glTF ORM textures.")
        return
        
    for rough in Path("TEXTURE").rglob("*_roughness.png"):
        prefix = str(rough).replace("_roughness.png", "")
        output = prefix + "_orm.png"
        
        # Resolve Ambient Occlusion maps
        filer = ""
        for occ_suffix in ("_occlusion.png", "_ao.png"):
            if os.path.exists(prefix + occ_suffix):
                filer = prefix + occ_suffix
                break
                
        fileg = str(rough)
        fileb = prefix + "_metallic.png" if os.path.exists(prefix + "_metallic.png") else ""
        
        cmd = magick + []
        if filer:
            cmd.append(filer)
        else:
            cmd.extend(["-size", "2048x2048", "xc:black"])
            
        cmd.append(fileg)
        
        if fileb:
            cmd.append(fileb)
        else:
            cmd.extend(["-size", "2048x2048", "xc:black"])
            
        cmd.extend(["-background", "black", "-channel", "RGB", "-combine", output])
        print(f"Assembling composite Occlusion-Roughness-Metallic texture: {Path(output).name}...")
        subprocess.run(cmd)

@task(category="image")
def crush():
    """Crush and resize image files located in the TEXTURE directory.

    Performs image scaling, sharpening, and posterization optimizations to compress texture assets.
    Saves optimized versions using a '_c' filename suffix (e.g. texture_c.jpg).
    Requires ImageMagick.

    Configuration Options:
      IMGSIZE       Dimensions to scale and gravity crop the images (default: 512x512).
                    Supports standard geometric parameters (e.g., IMGSIZE=1024x1024).
    """
    imgsize = config.get('IMGSIZE', '512x512')
    mogrify = get_mogrify_cmd()
    if not mogrify:
        print("Error: ImageMagick (mogrify) is required to batch crush texture assets.")
        return
        
    # Process JPG & PNG targets
    for img in list(Path("TEXTURE").glob("*.png")) + list(Path("TEXTURE").glob("*.jpg")):
        output = Path("TEXTURE") / f"{img.stem}_c.jpg"
        is_color = any(term in img.name.lower() for term in ("_col", "_dif", "_basecolor"))
        
        imposterize = ["-posterize", "136"] if is_color else []
        colorspace = ["-colorspace", "sRGB"] if is_color else []
        
        cmd = mogrify + [
            "-write", str(output), "-filter", "Triangle", "-define", "filter:support=2",
            "-resize", f"{imgsize}^", "-gravity", "Center", "-extent", imgsize,
            "-unsharp", "0.25x0.08+8.3+0.045", "-dither", "None"
        ] + imposterize + [
            "-quality", "82", "-define", "jpeg:fancy-upsampling=off",
            "-define", "png:compression-filter=5", "-define", "png:compression-level=9",
            "-define", "png:compression-strategy=1", "-define", "png:exclude-chunk=all",
            "-interlace", "none"
        ] + colorspace + [str(img)]
        
        print(f"Crushing file {img.name} -> {output.name}...")
        subprocess.run(cmd)
        
    # Process WebP targets
    for webp in Path("TEXTURE").glob("*.webp"):
        output = Path("TEXTURE") / f"{webp.stem}_c.webp"
        cmd = mogrify + [
            "-write", str(output), "-filter", "Triangle", "-define", "filter:support=2",
            "-resize", f"{imgsize}^", "-gravity", "Center", "-extent", imgsize,
            "-unsharp", "0.25x0.08+8.3+0.045", "-dither", "None", "-quality", "82", str(webp)
        ]
        print(f"Crushing WebP {webp.name} -> {output.name}...")
        subprocess.run(cmd)

@task(category="image", name="pngquant")
def run_pngquant():
    """Lossy PNG compressor, creating compressed web assets.

    Batches PNG textures located under the TEXTURE directory and compresses them recursively
    using lossy optimization. Outputs compressed files appended with '-fs8.png' suffix.
    Requires system installation of pngquant.
    """
    if not shutil.which("pngquant"):
        print("Error: pngquant utility was not found on your system.")
        return
        
    for png in Path("TEXTURE").glob("*.png"):
        if not png.name.endswith("-fs8.png"):
            print(f"Running lossy optimization on {png.name}...")
            subprocess.run(["pngquant", "--quality=65-80", str(png)])

# --- MAINTENANCE CATEGORY TASKS ---

@task(category="maintenance")
def update():
    """Update supporting files from local template repository.

    Identifies standard PROJECT_TEMPLATE directory locations upstream and synchronizes makefiles,
    environmental setups, and workspace configurations downstream. Supports rsync.
    """
    template_loc = None
    for p in ["../PROJECT_TEMPLATE", "../../PROJECT_TEMPLATE"]:
        if os.path.isdir(p):
            template_loc = p
            break
            
    if not template_loc:
        print("Error: Could not locate active PROJECT_TEMPLATE directory.")
        return
        
    print(f"Synchronizing codebase with templates folder: {template_loc}...")
    if shutil.which("rsync"):
        cmd = [
            "rsync", "-Arvth", "--existing", "--stats", "--progress", "--update",
            "--modify-window=1", f"{template_loc}/", "."
        ]
        if os.path.exists(".update-exclude"):
            cmd.append("--exclude-from=.update-exclude")
        subprocess.run(cmd)
    else:
        # Cross-platform fallback copier
        for root, _, files in os.walk(template_loc):
            for file in files:
                src = Path(root) / file
                rel = src.relative_to(template_loc)
                dest = Path(".") / rel
                if dest.exists() and dest.is_file():
                    if src.stat().st_mtime > dest.stat().st_mtime:
                        print(f"Synchronizing: {rel}")
                        shutil.copy2(src, dest)
    print("IMPORTANT: Examine local file logs and revert undesired codebase changes.")

@task(category="maintenance")
def feature():
    """Copy updated tasks and rules back to the PROJECT_TEMPLATE folder.

    Publishes changes and upgrades made to central configuration tools (like tasks.py or makefile)
    back to the upstream project templates folder for future instantiations.
    """
    template_loc = None
    for p in ["../PROJECT_TEMPLATE", "../../PROJECT_TEMPLATE"]:
        if os.path.isdir(p):
            template_loc = p
            break
            
    if not template_loc:
        print("Error: Could not locate PROJECT_TEMPLATE directory.")
        return
        
    print(f"Publishing features back to templates location: {template_loc}")
    # Safely copy primary orchestrators back to template
    targets = ["tasks.py", "makefile"]
    for t in targets:
        if os.path.exists(t):
            dest = Path(template_loc) / t
            print(f"Updating feature: {t} -> {dest}")
            shutil.copy2(t, dest)

# --- SYSTEM EXECUTION & HELP TARGETS ---

def show_task_help(task_name):
    """Parses and prints the full docstring of a target task in terminal-colored format."""
    if task_name not in TASKS:
        print(f"Error: Unknown task '{task_name}'")
        return
        
    meta = TASKS[task_name]
    print(f"\n{Colors.WHITE}Task:{Colors.RESET} {Colors.YELLOW}{task_name}{Colors.RESET} (Category: {meta['category']})")
    print("-" * (len(task_name) + 22))
    
    docstring = meta['func'].__doc__
    if docstring:
        # Normalize indentation dynamically
        lines = docstring.expandtabs().splitlines()
        indent = sys.maxsize
        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
                
        cleaned_lines = []
        if lines:
            cleaned_lines.append(lines[0].strip())
        for line in lines[1:]:
            if indent < sys.maxsize:
                cleaned_lines.append(line[indent:].rstrip() if len(line) > indent else "")
            else:
                cleaned_lines.append(line.rstrip())
        
        # Colorize parameter labels for better visibility
        formatted_doc = "\n".join(cleaned_lines)
        formatted_doc = re.sub(r'([A-Z_]{4,})', f"{Colors.YELLOW}\\1{Colors.RESET}", formatted_doc)
        print(formatted_doc)
    else:
        print("No detailed documentation provided for this task.")
    print()

@task(category="project")
def help():
    """Show this categorized help guide."""
    print(f"usage: python tasks.py [target]\n")
    print(f"To see detailed information and options for a specific task, run:")
    print(f"  {Colors.YELLOW}python tasks.py [target] --help{Colors.RESET}\n")
    
    categories = {}
    for t_name, t_meta in TASKS.items():
        cat = t_meta['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((t_name, t_meta['desc']))
        
    for cat in sorted(categories.keys()):
        print(f"{Colors.WHITE}{cat.upper()}:{Colors.RESET}")
        for t_name, desc in sorted(categories[cat]):
            spacing = " " * (16 - len(t_name))
            print(f"  {Colors.YELLOW}{t_name}{Colors.RESET}{spacing}{Colors.GREEN}{desc}{Colors.RESET}")
        print()

def main():
    if len(sys.argv) < 2 or clean_args[0] in ("-h", "--help", "help"):
        help()
        sys.exit(0)
        
    target_arg = clean_args[0].strip().lower().replace('_', '-')
    
    if target_arg in TASKS:
        # Check if task-specific help was requested
        if len(clean_args) > 1 and any(h in clean_args[1:] for h in ("-h", "--help", "help")):
            show_task_help(target_arg)
            sys.exit(0)
            
        try:
            # Execute registered task
            TASKS[target_arg]['func']()
        except KeyboardInterrupt:
            print("\nExecution interrupted by user.")
            sys.exit(1)
        except Exception as e:
            print(f"Error executing target '{target_arg}': {e}")
            sys.exit(1)
    else:
        print(f"Error: Unknown task target '{target_arg}'. Type 'python tasks.py help' for options.")
        sys.exit(1)

if __name__ == "__main__":
    main()