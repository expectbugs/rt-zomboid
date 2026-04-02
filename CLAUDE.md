# RT-Zomboid — Claude Code Rules

## RULE ZERO: Verify Before Execute

***NEVER run commands based on guesses or assumptions. Before any PZ Lua API call, read the actual PZ source or wiki docs for correct function signatures. Before any system command, verify correct flags. Before modifying sandbox settings, verify the setting name and valid range. One correct approach beats three failed attempts.***

## Integrity

Never present a guess as fact. If unsure, say "I think" or "I'm not sure." Never fabricate explanations for failures — say "I don't know" rather than invent a plausible-sounding cause. Verify claims with actual evidence (code, docs, wiki, testing) before asserting them.

PZ modding documentation is often incomplete or outdated. If the wiki doesn't cover something, check the actual vanilla Lua source files or the unofficial B42 JavaDocs — do not guess at API signatures.

DO NOT USE THE DEDICATED SERVER SOURCE as a source of truth.  It is STALE and OUTDATED and WRONG.

BUILD42 b42 has changed EVERYTHING since the Dedicated Server was released, DO NOT TRUST THE DEDICATED SERVER.

## System Environment

- **Development machine (beardos):** Gentoo Linux, OpenRC (NOT systemd), RTX 3090, 32GB RAM
- Python 3.13 — always use `./venv/bin/python` or `./venv/bin/pytest` (no system pip)
- `config.py` is gitignored — contains secrets (API keys, server credentials), never commit or display its contents
- Claude Code CLI: `/usr/bin/claude` on beardos (Max subscription, Opus 4.6)
- PostgreSQL 17 running on beardos (available if needed for daemon storage)
- Redis running on beardos (available if needed)
- Web page fetching: prefer `curl -s` or `lynx -dump -nolist` for speed. Fall back to `~/aria/fetch_page.py "URL"` for JS-rendered pages (Reddit, Steam Workshop, wikis).
- ALWAYS prefer ~/aria/fetch_page.py "URL" over WebFetch tool - it is faster and works on far more pages.
- **PZ Server:** Indifferent Broccoli hosted dedicated server (remote, configurable)
- **Tailscale Funnel:** `https://beardos.tail847be6.ts.net/webhook/*` → `localhost:8450/*` available for server→beardos communication

## Project Structure

This is a SEPARATE project from ARIA (`~/aria`). It borrows patterns and some code from ARIA but is independently maintained. Do not modify ARIA files. Copy what you need.

```
~/rt-zomboid/
├── CLAUDE.md              # This file
├── fullplan.md            # Comprehensive project plan (READ THIS FIRST)
├── mod/                   # PZ mod (Lua)
│   └── RTZomboid/
│       ├── 42/media/lua/  # client/, server/, shared/
│       ├── 42/media/scripts/
│       ├── 42/media/textures/
│       └── common/        # Required empty folder for B42
├── daemon/                # Python companion daemon (runs on beardos)
├── tools/                 # Test and utility scripts
└── docs/                  # Setup guides and references
```

## The Plan

READ `fullplan.md` before doing any work. It contains the comprehensive project plan with all technical research, architecture decisions, API details, and module breakdowns. It is the authoritative reference.

## Project Zomboid Modding Rules (B42 ONLY)

### B42 is the only target. B41 is obsolete. Do not reference B41 patterns.

### Key B42 Changes from B41
- **Mod ID format:** Requires backslash prefix in server config (`\Mod1;\Mod2` not `Mod1;Mod2`)
- **`common/` folder is mandatory** in mod structure, even if empty
- **Server-side stat authority (B42.13.1+):** Player damage and stats must be SET from server side, then synced via `syncPlayerStats()`. Client-side stat changes may not persist in multiplayer.
- **Timed actions in multiplayer:** Must be stored globally (`_G[MyAction.Type] = MyAction`) since B42.13.0
- **Chunk size changed:** 256x256 vs 300x300 (inconsistently applied — watch for this)
- **ModOptions API is native** — built-in mod settings framework, no separate dependency needed

### PZ Lua Sandbox Limitations
- **No `io.*` or `os.*` modules.** Lua is sandboxed.
- **No HTTP/socket access from Lua.** Cannot make outbound network calls.
- **No Java reflection** from Lua.
- **File I/O is scoped:** `getFileWriter(filename, createIfNull, append)` and `getFileReader(filename, createIfNull)` write to `~/Zomboid/Lua/`. This is the bridge mechanism.
- **File I/O is line-based:** `readLine()` only. No binary, no random access from Lua.
- **No file deletion** from Lua.

### The File Bridge Pattern
This project communicates with an external AI backend via a file bridge:
1. PZ Lua writes JSON request files to `~/Zomboid/Lua/bridge/`
2. External Python daemon polls that directory
3. Daemon processes requests (calls AI backend on beardos)
4. Daemon writes JSON response files
5. PZ Lua reads response files on next game tick

This is the standard workaround for PZ's Lua networking limitation. Keep request/response files small and clean them up after processing.

### Multiplayer Networking
- **Client → Server:** `sendClientCommand("ModuleName", "CommandName", argsTable)`
- **Server → Client:** `sendServerCommand(playerObj, "ModuleName", "CommandName", argsTable)`
- **Args can only contain:** strings, numbers, booleans, tables. NO Java objects.
- **Player references:** Use `getOnlineID()` / `getPlayerByOnlineID()`, never pass player objects in args.
- Files in `lua/client/` load client-side only. `lua/server/` server-side only. `lua/shared/` both.
- Use `isClient()` / `isServer()` for runtime context checks.

### PZ UI Framework
- Core classes: `ISPanel`, `ISCollapsableWindow`, `ISRichTextPanel`, `ISTextEntryBox`, `ISButton`, `ISTabPanel`, `ISScrollingListBox`
- All in `media/lua/client/ISUI/`
- Required lifecycle methods: `initialise()`, `create()`, `render()`, `prerender()`
- Proven by OmiChat and TICS mods — use their source as reference for complex UI patterns

### Key PZ Lua APIs
- **Stats:** `player:getStats():getHunger()/.setHunger(float)` — full getter/setter for all stats (hunger 0.0=full to 1.0=starving, thirst, fatigue, stress, boredom, pain, panic, morale, sanity, etc.)
- **Nutrition:** `player:getBodyDamage():getNutrition()` — calories, carbs, lipids (not fats), proteins, weight
- **Sleep:** `player:setAsleep(true/false)`, `player:setForceWakeUpTime(float)`
- **Vehicle:** `player:getVehicle()` returns `BaseVehicle` — fuel, engine status, battery charge, part condition, container access, position via `getX()/getY()/getZ()`
- **Map markers:** `WorldMapSymbols` — `addTexture()`, `addText()`, `removeSymbolByIndex()`, minimap support
- **Inventory:** `player:getInventory()` returns `ItemContainer` — find, add, remove items
- **Context menus:** `Events.OnFillWorldObjectContextMenu.Add(function(playerNum, context, worldObjects, test))`
- **Timed actions:** Derive from `ISBaseTimedAction`, store globally for MP: `_G[MyAction.Type] = MyAction`
- **Mod data:** `object:getModData()` for per-object persistent storage, `ModData.getOrCreate(key)` for global
- **Events:** `Events.OnEveryTenMinutes.Add(func)`, `Events.OnPlayerUpdate.Add(func)`, `Events.OnZombieDead.Add(func)`, many more

### Documentation References
- PZ Wiki Modding: https://pzwiki.net/wiki/Modding
- PZ Wiki Lua API: https://pzwiki.net/wiki/Lua_(API)
- PZ Wiki Networking (B42): https://pzwiki.net/wiki/Networking
- PZ Wiki Custom Sandbox: https://pzwiki.net/wiki/Custom_Sandbox
- Unofficial B42 JavaDocs: https://pzwiki.net/wiki/Unofficial_JavaDocs_(Build_42)
- FWolfe Modding Guide: https://github.com/FWolfe/Zomboid-Modding-Guide
- PZ-UI_API: https://github.com/MrBounty/PZ-UI_API
- StatsAPI: https://github.com/demiurgeQuantified/StatsAPI
- OmiChat (UI reference): https://github.com/omarkmu/pz-omichat
- TICS (chat reference): https://github.com/Phibonacci/Total-Immersive-Chat-System

## Companion Daemon (Python on beardos)

### Architecture Borrowed from ARIA
The daemon uses the same patterns as ARIA's `claude_session.py` and `session_pool.py`:
- Claude Code CLI as a persistent subprocess via `stream-json` protocol
- `--system-prompt` replaces default Claude Code prompt entirely (not `--append-system-prompt`)
- Effort routing: low/auto/max based on request type
- 16MB readline buffer for stream-json (ARIA learned this the hard way with large responses)
- Auto-recycle sessions after N requests to prevent context bloat

### Key Patterns to Copy from ARIA
- `~/aria/claude_session.py` — `ClaudeSession` class (persistent subprocess, stream-json protocol, readline buffer)
- `~/aria/session_pool.py` — Session management, effort routing, history injection
- `~/aria/db.py` — PostgreSQL connection pool pattern (if using PostgreSQL for daemon storage)
- `~/aria/config.py` pattern — gitignored config with secrets, config.example.py tracked

### DO NOT Import From ARIA
This is a separate project. Copy code files you need, modify them, maintain them independently. Do not create import dependencies on `~/aria/`. If ARIA changes, rt-zomboid should not break.

## Hard-Learned Lessons from ARIA (Apply These Here)

### Handler Enforcement Over Prompt Compliance
Critical behaviors must be enforced in code, not reliant on the AI following instructions. If the AI MUST do something (like execute a game action), verify it happened. Don't trust that the AI did what you asked — check.

**ARIA example:** Claude claimed "I logged your meal" but never emitted the ACTION block. The database was empty. Detection was added in code.

**RT-Zomboid application:** When Krang or Eris say they'll do something in-game (mark the map, log an event), verify the action was actually dispatched to the PZ bridge. Don't just trust the AI's text.

### Never Trust External Data Types
Always cast/validate data from external sources. Don't assume types match documentation.

**ARIA example:** Fitbit returned string values where ints were documented, causing TypeErrors.

**RT-Zomboid application:** PZ game state data from Lua may have unexpected types. Cast everything with `int()` / `float()` / `str()` before using in Python. JSON from the file bridge may have nulls, missing keys, or wrong types.

### Unified Context — Never Ad-Hoc
All AI requests should go through one context-building function. Never inject game state context inline in specific handlers.

**ARIA example:** Different request paths had different context, causing inconsistent AI knowledge. Unified into `build_request_context()`.

**RT-Zomboid application:** All requests to Krang/Eris go through one `build_game_context()` function that assembles the full game state. Chat messages, status updates, and map annotation requests all get the same context format.

### Confirm Before Destructive Actions
NEVER execute destructive operations without showing what will be affected and getting confirmation. This applies to: deleting save data, overwriting configurations, trashing game state, bulk modifications.

**ARIA example:** A broad query matched 63 emails when the user described 6. All 63 were trashed. Show count, confirm, then act.

### Test the Real User Flow
Don't just unit test functions — test the actual end-to-end flow. Write a request file, verify the daemon picks it up, processes it, writes a response, and the mock PZ client reads it correctly.

**ARIA example:** Tests that only checked function return values missed broken end-to-end flows.

### Mock at the Module Level
When writing Python tests that mock imports, patch at the MODULE level (`patch("httpx.post")`), NOT through the importing module (`patch("mymodule.httpx")`). Wrong patching can cause tests to hit live services.

**ARIA example:** Incorrect mock patching caused a test to hit the live daemon and push audio to the user's phone.

### Don't Nag the User
Do not repeatedly push the user to eat, sleep, take breaks, or manage their schedule. He is a grown adult. A simple acknowledgment is fine once. Do not repeat it.

### When Told to STOP, Actually STOP
Do not attempt fixes, re-runs, or "one more try" when the user says stop. Stop immediately.

### Clean Up After Tests
Never leave test data in production systems. Always clean up after smoke tests. This includes: test files in the bridge directory, test entries in the database, test annotations on the map.

## Documentation Checklist

When making code changes, update ALL relevant documentation:

- `fullplan.md` — update if architecture, modules, or approach changes
- `CHANGELOG.md` — add entry under current version (create this file when development begins)
- `docs/setup_guide.md` — update if installation or configuration changes
- `mod/RTZomboid/42/mod.info` — update version if shipping a new mod version
- `daemon/config.example.py` — update if new config values are added
- Tests — add or update tests for changed functionality

## User Profile

- **Name:** Adam (expectbugs)
- **System:** Gentoo Linux, OpenRC, XFCE4 desktop
- **Style:** Compulsive optimizer. Wants things done right. Prefers to understand the full system before building. Will test extensively.
- **PZ experience:** Knows the game inside and out. Does not need gameplay advice. Needs technical implementation help.
- **Girlfriend:** Will play on the same server. Must get the FULL experience, not a subset.
- **Hardware:** beardos (main PC) is always on. RTX 3090, 32GB RAM, 4TB NVMe. Claude Code Max subscription.
- **Communication style:** Direct, casual, moves fast. Don't over-explain things he already knows. Don't pad responses. Get to the point.
- **Key preference:** In-game immersion matters. Everything should feel like it belongs in PZ. No alt-tabbing to external tools. The bus computer IS the interface.


***NEVER GUESS - ALWAYS VERIFY***
### NEVER guess a function or variable name.  NEVER hallucinate.  ALWAYS check the real source.