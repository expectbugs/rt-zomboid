# RT-Zomboid: Real-Time Apocalypse Bus

A persistent, real-time Project Zomboid B42 world with AI companions. An Apocalypse Bus serves as home base with two AI personalities — **Krang** (strategic operations) and **Eris** (chaotic companionship) — living in the bus computer system.

Your real day is your PZ day. 24-hour real-time days, synced to the real clock. Tab away to work — your character stays safe in the bus, auto-managed by Krang. Come back and pick up where you left off.

## Architecture

```
PZ Client (beardos)              Companion Daemon (beardos)
     │                                    │
  Client Lua                        Python + Claude CLI
  writes JSON request               polls directory
     │                                    │
     └── ~/Zomboid/Lua/RTZomboid_Bridge/ ─┘
              request/response files
```

- **PZ Lua mod** — collects game state, writes JSON request files, polls for responses
- **Python daemon** — polls bridge directory, routes to Krang/Eris Claude sessions, writes responses
- **File bridge** — both sides on the same machine (beardos), no network needed

## Project Structure

```
rt-zomboid/
├── mod/RTZomboid/          # PZ mod (Lua)
│   ├── 42/
│   │   ├── mod.info
│   │   └── media/lua/
│   │       ├── client/     # Client bridge (file I/O, polling)
│   │       ├── server/     # (future: AFK survival, exploration tracking)
│   │       └── shared/     # JSON encoder, constants
│   └── common/             # Required empty folder for B42
├── daemon/                 # Python companion daemon
│   ├── companion_daemon.py # Main entry point + AI personality prompts
│   ├── claude_session.py   # Persistent Claude CLI subprocess manager
│   ├── bridge.py           # File bridge polling + response writing
│   ├── game_context.py     # Game state → AI context formatter
│   ├── memory_store.py     # SQLite storage (conversations, events)
│   ├── config.example.py   # Configuration template
│   └── config.py           # Local config (gitignored)
├── tools/
│   └── test_bridge.py      # End-to-end bridge test (no PZ needed)
├── fullplan.md             # Comprehensive project plan
└── CLAUDE.md               # Claude Code development rules
```

## Setup

### Prerequisites

- Project Zomboid Build 42
- Python 3.13+
- Claude Code CLI (`/usr/bin/claude`) with Max subscription

### PZ Mod

Symlink the mod into PZ's mod directory:

```bash
ln -s /path/to/rt-zomboid/mod/RTZomboid ~/Zomboid/mods/RTZomboid
```

Enable "RT-Zomboid" in the PZ mod list.

### Companion Daemon

```bash
cd rt-zomboid
python3 -m venv venv
cp daemon/config.example.py daemon/config.py
# Edit daemon/config.py if needed

./venv/bin/python daemon/companion_daemon.py
```

### Test Without PZ

```bash
# Start daemon in one terminal, then:
./venv/bin/python tools/test_bridge.py krang "What's our status?"
./venv/bin/python tools/test_bridge.py eris "Hey, what's up?"
```

## Current Status

**Phase 1 complete** — end-to-end communication working:
- PZ mod loads, collects game state, writes bridge requests
- Daemon polls, routes to Krang/Eris Claude sessions, writes responses
- Responses appear in PZ console

See `fullplan.md` for the full roadmap (8 modules across 4 phases).
