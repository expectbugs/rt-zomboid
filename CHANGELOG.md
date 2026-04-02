# Changelog

## v0.2.0 — 2026-04-02

Terminal UI, ambient chatter, unified AI history.

### Added
- **Bus Intelligence Terminal UI** (F9 hotkey)
  - ISCollapsableWindow with rich text message log, text entry, send button
  - Color-coded messages: Krang (green), Eris (purple), player (white), system (amber)
  - Resizable window, scrollable message history (200 line buffer)
  - Chat commands for multiplayer: /rtui, /krang, /eris

- **Ambient Chatter Engine** (`daemon/ambient.py`)
  - Krang solo observations: periodic environmental/status notes (10-20 min)
  - Eris solo quips: bored/funny unprompted comments (15-30 min)
  - Krang/Eris banter: 2-4 exchanges with natural delays (20-40 min)
  - Krang observation -> 25% Eris reacts -> 25% Krang replies -> Eris always responds
  - 12.5% chance Krang ends banter with terse closer ("...", "Ugh.", "Indeed.")
  - Name-addressing forces the named AI to respond
  - Push message system: daemon writes rt_push.json, Lua polls with 4s debounce

- **Unified Conversation History**
  - Both AIs now see each other's messages in context
  - get_recent_unified() queries all personalities for a player
  - History formatted with speaker labels (KRANG/ERIS/HUMAN)

### Changed
- **Krang personality**: more formal and system-like, terse status reports, ship's computer voice
- **Eris personality**: swears naturally, much stronger variety requirements, explicit anti-repetition rules
- **Both AIs**: strict anti-repetition — must check history, never repeat topics from last 5 messages
- **Both AIs**: strict in-character rules — no 4th wall breaking, no game mechanics references
- Injury tracking: collects body part injuries (scratched, deep wound, bitten, bleeding, fracture, splinted, bandaged)
- Month/day now 1-indexed (was 0-indexed, causing Krang to think July was "6 months in")
- Temperature converted to Fahrenheit in context builder
- JSON responses use ensure_ascii=False (fixes unicode escape spam in UI)

### Fixed
- JSON encoder rewritten for Kahlua: no rawget, next, string.byte, math.huge, string.format(%g), gsub(TABLE)
- Push message deduplication: 2s file lifetime + 4s Lua debounce = exactly one read per push
- Boot request removed (was spamming Krang on every game start)

## v0.1.0 — 2026-04-01

Phase 1: Foundation — Mod scaffold, file bridge, companion daemon.

### Added
- **PZ Mod (RTZomboid)**
  - B42 mod scaffold with mod.info, shared constants, client bridge
  - JSON encoder/decoder written specifically for PZ's Kahlua Lua VM (no rawget, next, string.byte, math.huge — all functions verified against B42 vanilla client source)
  - Client bridge: writes JSON requests to `~/Zomboid/Lua/RTZomboid_Bridge/`, polls for responses every ~500ms via OnTick
  - Game state collection: player stats (hunger, thirst, fatigue, etc. via B42 CharacterStat enum), health, position, indoor/outdoor, weather (temperature, precipitation)
  - Auto-sends boot request to Krang on game start

- **Companion Daemon (Python)**
  - Persistent Claude CLI session manager adapted from ARIA project (16MB readline buffer, stream-json protocol, control_request handling, full assistant text collection)
  - File bridge: polls for requests, atomic response writes (.tmp → rename), startup cleanup, stale response cleanup
  - Krang personality: strategic operations AI — morning briefings, supply tracking, dry humor
  - Eris personality: chaotic companion AI — entertainment, sarcasm, relationship tracking
  - Unified game context builder with defensive type casting
  - SQLite storage for conversations, events, relationship scores
  - Effort routing framework (chat/status/system)

- **Tools**
  - `test_bridge.py`: end-to-end test that simulates PZ Lua file writes

### Technical Notes
- B42 changed Stats API from `stats:getHunger()` to `stats:get(CharacterStat.HUNGER)` — verified against actual B42 client source, not stale dedicated server files
- `getMonth()` and `getDay()` are 0-indexed in Kahlua — vanilla adds +1 for display
- PZ's Kahlua VM lacks: `next()`, `rawget(table, number)`, `string.byte()`, `math.huge`, `string.format(%g)`, `string.gsub(str, pat, TABLE)`
- Temperature reported in Fahrenheit (converted from Celsius in context builder)
