"""RT-Zomboid Companion Daemon configuration.

Copy to config.py and edit. config.py is gitignored.
"""
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BRIDGE_DIR = "~/Zomboid/Lua/RTZomboid_Bridge"  # expanded at runtime

# --- Claude Code CLI ---
CLAUDE_CLI = "/usr/bin/claude"
CLAUDE_TIMEOUT = 600          # seconds per query
SESSION_RECYCLE_AFTER = 150   # recycle session after N requests

# --- Session Effort ---
DEFAULT_EFFORT = "auto"       # "low", "auto", or "max"

# --- Bridge ---
POLL_INTERVAL = 0.5           # seconds between bridge polls
RESPONSE_TTL = 300            # seconds before stale responses are cleaned

# --- Database ---
DB_PATH = str(DATA_DIR / "rt_zomboid.db")

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = str(BASE_DIR / "logs" / "daemon.log")
