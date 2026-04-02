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

# --- Ambient Chatter Intervals (seconds) ---
AMBIENT_KRANG_MIN = 600       # 10 minutes
AMBIENT_KRANG_MAX = 1200      # 20 minutes
AMBIENT_ERIS_MIN = 900        # 15 minutes
AMBIENT_ERIS_MAX = 1800       # 30 minutes
AMBIENT_BANTER_MIN = 1200     # 20 minutes
AMBIENT_BANTER_MAX = 2400     # 40 minutes

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = str(BASE_DIR / "logs" / "daemon.log")
