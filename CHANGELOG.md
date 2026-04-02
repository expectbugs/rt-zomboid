# Changelog

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
