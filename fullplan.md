# RT-Zomboid: AI Companions for the Apocalypse

## The Vision

A persistent, real-time Project Zomboid world with AI companions that live in your base's computer system. Build a shelter anywhere -- a house, a warehouse, a bus, a walled compound -- and install a computer terminal to bring Krang online. He monitors your base, tracks every item in every container, watches security cameras, manages automated defenses while you sleep, and keeps you alive with supply suggestions and threat warnings. Eris shows up uninvited sometime later and refuses to leave.

Communicate with them at the terminal, over walkie-talkie (same town range), or via HAM radio (any distance). Your girlfriend can drop in and out on a shared multiplayer server, build her own base with her own terminal, or share yours.

The world runs on 24-hour real-time days synced to the real clock. Everything is earned through gameplay. No safe spaces handed to you.

---

## Platform & Server

- **Game:** Project Zomboid Build 42 (B42 only)
- **Server:** Indifferent Broccoli hosted dedicated server
  - Tailscale connectivity to beardos
  - Server-side mods supported, `DoLuaChecksum=false`
- **Players:** 2 (Adam + girlfriend), both get the full experience
- **AI Backend:** beardos (Gentoo, RTX 3090, Claude Code CLI)
- **Always-on:** PZ server runs 24/7. Client on beardos, tab in/out.

---

## Core Mod Dependencies

### [B42] Project RV Interior (Mickey Knox)
- Workshop ID: 3543229299
- Optional -- nice for bus living. RT-Zomboid overrides ATAApocalypseBus to 4x12 colossal interior.

### ATA Bus + Apocalyptic Bus Addon
- Workshop IDs: 3402812859, 3543222473
- Apocalyptic Bus spawns naturally in the world. Cool vehicle, not required.

### Immersive Solar Arrays [B42 MP]
- Powers terminal, cameras, alarm system, automated defenses.

### StatsAPI (demiurgeQuantified)
- Stat calculation hooks for RealTime Rebalance.

---

## What's Built (v0.2.0)

- File bridge (Lua <-> Python daemon via JSON files)
- Companion daemon (persistent Claude CLI sessions for Krang/Eris)
- Terminal UI (F9 hotkey, color-coded chat, resizable)
- Ambient chatter (solo observations, quips, banter with cooldowns)
- Unified conversation history (both AIs see each other)
- Game state collection (CharacterStat enum, injuries, position, weather)
- JSON encoder for Kahlua (no rawget, next, string.byte, math.huge)
- Bus interior override (ATAApocalypseBus -> 4x12 colossal)

---

## Module A: Session Reset

### Problem
Krang and Eris carry memory across saves. New game = stale context.

### Solution
- On game start, send world/save identifier to daemon
- Daemon compares to stored ID. If different: clear conversations, reset scores
- Krang and Eris boot fresh

---

## Module B: Placeable Computer Terminal

### Concept
Krang comes online when you place and power a computer terminal. Not before.

### Implementation
- **Craftable item:** "Salvaged Terminal" -- Desktop Computer + 2x Electronic Scrap + Screwdriver (Electrical 2)
- **Placement:** Standard furniture placement on any indoor tile
- **Power:** Must be on powered tile (generator or solar)
- **Activation:** Right-click -> "Boot System"
- **One per player.** Terminal coordinates stored in ModData = "home base."

### Access Methods (NO F9 global hotkey in production)
- **At terminal:** Right-click -> "Use Terminal" opens full UI (chat + systems + inventory)
- **Walkie-talkie:** Craftable item. Right-click in inventory -> opens simple chat-only UI. Range: same town (~200 tiles clear, degrades to ~500, dead beyond 800).
- **HAM Radio:** Requires one HAM radio at Krang's building AND one the player carries or finds. Unlimited range. Opens simple chat-only UI.
- **Out of range:** Walkie-talkie still lets you type. Message just doesn't arrive. No error. No response. No ambient chatter. Silence. You're alone.

### Eris Delayed Arrival
- Eris does NOT come online when the terminal boots
- She appears randomly between 2 real-time hours and 4 real-time days after Krang
- Krang has no idea she's coming
- When she arrives, she announces herself. Krang is surprised and annoyed.
- From then on, she's permanent

---

## Module C: Krang's Knowledge Database

### Concept
Krang has access to a game knowledge database -- recipes, TV schedules, skill requirements, VHS tape contents, crafting info. He's a survival encyclopedia without breaking immersion. The data is framed as being stored in the terminal's hard drive from before the outbreak.

### What Krang Knows
- **All recipes:** What's needed, what skill level, what tools
- **TV show schedules:** Which channels, which shows teach skills, what times
- **VHS tapes:** Which tapes teach what skills and at what level
- **Skill requirements:** What level is needed for specific crafting/building tasks
- **Item properties:** Nutrition values, weapon stats, medical supply uses
- **Building types:** What loot is typically found in pharmacies, warehouses, gun stores, etc.

### Implementation
- Extract game data from PZ script files into a reference document
- Inject as part of Krang's system prompt or as a retrievable context block
- Krang answers questions naturally: "You need Carpentry 4 for that. And a hammer."

---

## Module D: Full Inventory Tracking

### Concept
Krang maintains a complete database of every item in the building -- every container, every shelf, every crate, every character's inventory (including bags), items on the ground, vehicle containers within range. Not furniture -- contents.

### What Krang Tracks
- Every container in the building and its contents
- Every player's inventory including equipped bags
- Items dropped on the ground inside the building
- Vehicle containers (parked near base)
- Item condition (worn hammer, nearly-empty lighter, spoiling food)

### Shopping Lists
Based on inventory tracking, Krang proactively suggests what to look for:
- "Last hammer is at 30% condition. Grab another if you see one."
- "Canned food down to 4 days supply. Priority target."
- "No antibiotics. Veterinary clinic two blocks north might have some."
- "Light bulb count: 2. Grab more before we're in the dark."

### Implementation
- Periodic building scan (every few game-minutes) collects all container contents
- Structured inventory data sent to daemon with bridge requests
- Krang's context includes summarized inventory with quantities and conditions
- Shopping list generated by comparing inventory against configurable thresholds

---

## Module E: Building Awareness

### Concept
Krang sees everything inside his building and a few tiles outside.

### What Krang Monitors
- **Interior:** All rooms, all floors, all doors/windows (open/closed/damaged/barricaded)
- **Exterior (3-5 tiles out):** Generators, solar panels, rain collectors, immediate surroundings
- **Multi-floor:** Full building from basement to roof
- **Power systems:** Generator fuel level, condition, solar output, battery charge

### Reports
- "Back door is open."
- "Rain collector is full. Good time to fill bottles."
- "Generator at 40% fuel. Maybe 8 hours left."
- "South wall window is damaged. One good hit and it's gone."

---

## Module F: Security Cameras

### Concept
Craftable cameras extend Krang's vision. Must be powered by the same electrical system as the terminal.

### Implementation
- **Craftable:** Video Camera + Electronic Scrap + Wire + Screwdriver (Electrical 3)
- **Wall-mounted**, indoor or outdoor
- **Coverage:** 15-20 tile radius per camera
- **Powered:** Must be on same electrical grid as terminal
- **Krang sees:** Zombies, vehicles, players, doors/windows, ground items
- **Named cameras:** Player names them on placement ("North Gate", "Parking Lot")

### Reports
- "Camera 'North Gate': 3 zombies, 40 tiles out. Moving east."
- "Camera 'Parking Lot': Vehicle still there. No activity."
- "Movement on 'West Fence'. Six zombies approaching."

---

## Module G: Alarm System

### Concept
Zombie breach detection with alerts.

### Implementation
- **Craftable:** "Alarm Panel" -- Electronic Scrap + Wire + Speaker + Screwdriver (Electrical 3)
- **Triggers:**
  - Zombie detected inside building
  - Door/window broken
  - Large group (5+) within 10 tiles of any camera
- **Effects:**
  - Krang announces breach location and count
  - Alarm sound plays in-game
  - "RED ALERT. Ground floor, east side. Two inside, more at the door."
  - "All clear. Threat neutralized. South window needs repair."

---

## Module H: Automated Defenses (AFK Protection)

### Concept
When the player is AFK (at work, sleeping IRL), Krang can activate automated defenses IF the player has built them and has the skill level to have built them. Keeps the base from being overrun during real-life obligations.

### Defense Types
- **Noise traps:** Lure zombies away from base (timer-activated, crafted)
- **Electric fences:** Damage/slow zombies at perimeter (Electrical 5+, requires power)
- **Automated turrets:** If feasible within PZ mechanics. May need to be simulated rather than actual projectiles.
- **Reinforced barricades:** Extra-strength barricades that Krang can "virtually repair" by consuming stored materials while player is AFK

### Krang's Role
- Activates defenses when player goes AFK (no input for X minutes)
- Manages fuel/ammo/material consumption
- Logs everything: "3:14 AM -- 6 zombies approached east fence. Electric fence neutralized 4. Noise trap diverted 2."
- Reports summary when player returns

---

## Module I: AFK Auto-Survival

### Concept
Krang auto-manages basic needs when player is in base.

### Requirements
- Player inside building with powered terminal
- Food/water available in base containers
- Krang auto-feeds, hydrates, manages sleep based on stat thresholds
- Logs everything for morning briefing

---

## Module J: Reimagined Radio

### Walkie-Talkie
- Craftable: Walkie Talkie + Electronic Scrap + Battery + Screwdriver (Electrical 2)
- Range: ~200 tiles clear, degrades to ~500, dead beyond 800
- Simple chat-only UI
- Out of range: messages silently fail, no ambient chatter

### HAM Radio
- Requires one HAM radio at Krang's building, one with the player
- Unlimited range
- Same simple chat UI
- Two-way: Krang can reach you too (push messages still work)

---

## Module K: Auto-Annotated Map

### Concept
Track exploration, auto-mark the in-game map.

### Annotation Types
- Green check: Cleared building
- Red skull: Dangerous (many zombies, player death)
- Blue box: Loot found
- Yellow star: Player-marked POI
- Orange warning: Near-death experience
- Red X: Player death location

### Implementation
- Track building visits, zombie kills per location, container interactions
- Krang generates annotations from exploration data
- Portable "Salvaged Tablet" for map access in field

---

## Module L: RealTime Rebalance

### 24-Hour Days Synced to Real Clock
- Game calendar and clock match real time
- Main challenge: syncing at world creation and maintaining sync
- Most game systems already scale with hours-per-day setting
- Test first, add Lua hooks only where things feel wrong

### Skill Book Overhaul
- Single book per skill replaces 5-volume system
- Gradual XP multiplier increase as you read
- 8+ real-time hours to fully read one book

### What Probably Just Works at 24h
- Hunger/thirst (game-time based)
- Crop growth (game-time based)
- Generator fuel consumption
- Zombie respawn (configurable hours)

### What Might Need Adjustment
- Sleep duration
- Boredom/stress accumulation
- Wound healing rates
- Bandage degradation timing

---

## Module M: Power Budget Management

### Concept
Krang tracks power consumption vs generation and advises on energy management.

### Reports
- "Running 3 cameras, fridge, and terminal. Solar covers daytime. Drawing batteries down at night."
- "Consider shutting Camera 3 overnight. We're burning 20% more than we generate."
- "Generator fuel won't last through tomorrow at this rate. Prioritize a fuel run."

---

## Planned Features

### Threat Assessment Heatmap
Krang rates danger levels by direction from base using camera data and historical zombie movement. "North is hot today. East has been quiet for three days. I'd go east."

### Zombie Horde Prediction (Requires Outposts)
Requires building security camera outposts at remote locations (camera + HAM radio + computer). Krang uses meta migration data from outpost areas to predict zombie movement. "Outpost East detected heavy migration southwest. That's headed our way. 6-12 hours out. Recommend early lockdown." Without outposts, Krang only knows about his immediate camera range.

### Kill Board
Krang tracks zombie kills per player, per weapon, per location (integrates with KillCount mod data). Eris turns it into a competition between players. "Adam: 47. Your girlfriend: 52." Eris: "She's making you look bad."

### Eris's Nicknames
Eris develops personalized nicknames based on player behavior. Hoarder gets "Dragon." Frequent death gets "Respawn." Reckless player gets "Yolo." Nicknames evolve as behavior changes over time.

### Loot Memory
Krang tracks every item the player has SEEN in containers while exploring -- not just what they took, but what they left behind. When a need arises later, Krang can recall where items were spotted. "You need a hammer? You saw three of them at the hardware store on Oak Street, day 4. Want me to mark it?" Loot memory is timestamped so Krang can flag stale data: "That was 2 weeks ago. Someone else may have grabbed it by now." Krang can also remove map annotations that are no longer relevant (looted, outdated, or player-requested removal).

### Supply Run Suggestions
Krang suggests areas based on building types, shopping list needs, AND loot memory. For unvisited buildings he knows what's likely from building type data. For visited buildings he knows exactly what was there. "We need medical supplies. You left antibiotics at the pharmacy on 3rd Street last Tuesday. Also, the vet clinic north of here is unexplored -- good odds." Can mark targets on the map and remove marks when no longer needed.

### Weather Forecasting
Krang predicts weather and advises accordingly. "Rain expected tomorrow. Good day to stay in and craft. The collector should fill up."

### Base Defense Blueprints
Krang suggests optimal barricade placement, choke points, and escape routes based on building layout scans. "Three ground-floor entry points. South door is weakest. Double-barricade it and funnel any breach through the hallway."

### Eris's Radio DJ Mode
Eris occasionally "takes over the comms" and does mock radio broadcasts. Apocalypse news, fake ads, survivor tips in her chaotic style. "This is Radio Free Eris coming to you live from a stolen CPU cycle..."

### Base Upgrade Priority Queue
Krang maintains a prioritized list of recommended improvements. "Priority 1: Barricade south wall. Priority 2: Second rain collector. Priority 3: Backup generator." Updates dynamically.

### Terminal Games (Floppy Disk Loot)
Lootable floppy disk items found in houses, offices, and stores. Each disk contains a classic text game. Right-click the terminal with disks in inventory or nearby (2-3 tiles) to see a "Game Disks" submenu listing available games. Selecting one opens the game in a SEPARATE TAB on the terminal -- so Krang and Eris can comment from their own tab without interfering with gameplay.

**Games (each a separate floppy disk item):**

Works now (clean stdin/stdout text I/O):
- "Zork I" -- Frotz engine, the classic dungeon crawl
- "Hitchhiker's Guide to the Galaxy" -- Frotz engine, Douglas Adams absurdity
- "Anchorhead" -- Frotz engine, Lovecraftian horror (fits the mood)
- "ChessMaster 2000" -- Chess via Stockfish, retro branding
- (Any Frotz-compatible interactive fiction can be added as a disk)

Blocked on ncurses rendering (see Possible Future Ideas):
- "Hack" -- Nethack
- "Angband" -- Tolkien/D&D dungeon crawler
- "Brogue" -- elegant roguelike

**MUD Access (separate loot item: "Network Access Card"):**
- Found in offices, server rooms, university buildings
- When used at terminal, Krang connects to a MUD server
- Fiction: "Found a server still running on a university UPS somewhere. Don't ask me how."
- Daemon connects via TCP to a running MUD server (hosted locally on beardos or remote)
- Same text I/O pipe pattern as Frotz
- Opens in its own terminal tab
- Eris makes a character and causes problems

**Implementation:**
- Custom items: `FloppyDisk_Zork`, `FloppyDisk_HHGTG`, `FloppyDisk_Hack`, `FloppyDisk_Chess`
- Spawn in loot tables: houses, offices, school desks, filing cabinets (reasonable frequency)
- Daemon runs the actual game engine (Frotz, Stockfish, etc.) as a subprocess
- Game I/O relayed through the bridge like AI chat, but tagged as "game" type
- Terminal UI opens a new tab for the active game with monospace text output
- Eris reacts to game events from her tab: "You got eaten by a grue? Skill issue."
- Krang occasionally comments: "I have a map of that dungeon if you want it. I won't judge."

**Spawn rates:** Generous. These are fun, not rare endgame loot. Every few houses should have a disk or two. Offices are goldmines.

### Perimeter Patrol Suggestions
Based on camera coverage gaps, Krang suggests patrol routes. "Blind spot between cameras 2 and 3. 15-tile gap along the north fence. Patrol sweep recommended or install a third camera."

### Scavenging Intel Database
Krang knows building types and their typical loot (from pre-outbreak terminal data). Combines with map exploration data for targeted suggestions.

---

## Possible Future Ideas

These are good concepts but need significant R&D or are end-game polish. Tabled for later.

### Krang's Learning System
Krang tailors advice based on observed player patterns -- what you loot, where you go, when you play. "You always come back from warehouses with tools but no food." Tricky to implement correctly without being annoying or wrong.

### Eris's Secret Projects
Eris announces she's been "working on something" and reveals small useful discoveries. Needs careful design to feel earned rather than random handouts.

### Companion Morale System
Both AIs have mood that shifts with circumstances. Krang more terse when supplies are critical. Eris quieter when things are genuinely bad. Both perk up after wins. End-game personality polish after everything else works.

### ncurses Games (Blocked on Terminal Rendering)
Many great ASCII games use ncurses for raw terminal control — cursor positioning, screen redraws, color codes. Our PZ terminal is an ISRichTextPanel that only does line-by-line colored text, not a real terminal emulator. Piping ncurses output through the JSON bridge would produce garbage escape codes instead of a usable display.

**Solving this unlocks ALL of these at once:**
- Cataclysm: DDA — open source zombie survival roguelike (the irony)
- Nethack — if we want the real ncurses version, not a simplified pipe
- Angband — same ncurses issue
- Brogue — same
- DiabloRL — open source Diablo 1 roguelike (FreePascal, SourceForge)
- Dwarf Fortress adventure mode — same but also absurdly complex

**Possible solutions (all nontrivial):**
- Run a terminal emulator lib in Python (e.g. pyte) that interprets ncurses output into a character grid, then serialize the grid as text for the PZ terminal to render
- Fork the games to use a simplified line-based output mode
- Build a minimal VT100 interpreter into the PZ terminal UI

Until this is solved, only games with clean stdin/stdout text I/O work (Frotz interactive fiction, Stockfish chess). The floppy disk games on the main list are limited to those.

### ASCIIliens (ASCII Space Invaders)
Turn-based ASCII Space Invaders clone in Rust (GPL-3.0). Each keypress advances one frame — no framerate issues. Would need input adaptation (raw terminal keys -> text commands through bridge). Source: https://github.com/christimahu/asciiliens

### First-Person ASCII Dungeon Crawler
Wizardry-style first-person dungeon crawler rendered with ASCII wireframe corridors (/ \ | _ characters). The open-source scene for this is nearly nonexistent — would likely need to be built from scratch. A Python raycaster with ASCII output on the daemon side, turn-based, piped through the terminal. Not complex in theory but a project unto itself. Would be a floppy disk item: "Dungeons of Knox" or similar.

### Terminal Music Player
Lootable "Music CD" items. Insert into terminal to play. Daemon runs a system audio player (mpv/ffplay) on beardos while Lua mutes PZ music via getSoundManager():StopMusic() and getCore():setOptionMusicVolume(). Stopping the in-game player restores PZ music. Music comes from system speakers, not FMOD -- but same speakers so player wouldn't notice. Needs a music directory on beardos to scan. Feasible but hacky.

---

## Build Order

```
DONE (v0.2.0):
  File bridge, daemon, terminal UI (F9), ambient chatter,
  unified history, game state collection, bus interior override

Phase 1 -- Fixes & Foundation:
  Module A: Session reset on new game
  Module B: Placeable terminal + access methods (terminal/walkie/HAM)
  Module B: Eris delayed arrival system
  Replace F9 with item-based access (terminal/walkie/HAM)

Phase 2 -- Base Intelligence:
  Module C: Krang's knowledge database (recipes, TV, skills)
  Module D: Full inventory tracking + shopping lists
  Module E: Building awareness (doors, windows, power, floors)
  Module M: Power budget management

Phase 3 -- Security & Defense:
  Module F: Security cameras
  Module G: Alarm system + night watch (auto-close doors on zombie approach)
  Module H: Automated defenses (AFK protection)

Phase 4 -- Survival & Field:
  Module I: AFK auto-survival (auto-feed, hydrate, sleep)
  Module J: Radio system (walkie-talkie + HAM radio)
  Module L: RealTime rebalance (24h days, clock sync)

Phase 5 -- Exploration & Intelligence:
  Module K: Auto-annotated map
  Supply run suggestions (based on building types + shopping list)
  Threat assessment heatmap
  Weather forecasting
  Scavenging intel database

Phase 6 -- Entertainment & Social:
  Terminal games (floppy disk loot -- Zork, HHGTG, Nethack, Chess)
  Kill board (integrates with KillCount mod)
  Eris's nicknames
  Eris's radio DJ mode

Phase 7 -- Advanced:
  Base defense blueprints
  Base upgrade priority queue
  Perimeter patrol suggestions
  Zombie horde prediction (requires camera outposts)
```

---

## Risk Assessment

### High Risk: Building Scan Performance
Scanning all tiles + containers in a building every few minutes. Must verify PZ APIs for building iteration and benchmark. May need throttling or incremental scanning.

### High Risk: 24h Clock Sync
Keeping PZ game clock synced to real wall clock across server restarts and time zone changes. No known mod does this -- may require creative solutions.

### Medium Risk: Custom Items in B42
B42 changed crafting/recipe systems significantly. All item definitions must be verified against current B42 script format.

### Medium Risk: Security Camera Power Detection
Need to verify PZ APIs for checking if two tiles share an electrical source. May need proximity-based detection instead of true grid connectivity.

### Medium Risk: Automated Defense Feasibility
PZ may not expose APIs for programmatic zombie damage or noise generation. May need to simulate defenses through stat manipulation rather than actual game mechanics.

### Low Risk: AI Quality
Already working well. Prompt tuning is ongoing but not blocking.

---

## What This Creates

1. **Your base is YOUR base.** Build anywhere. Install a terminal. Krang wakes up, scans your building, inventories your supplies, and starts keeping you alive. Add cameras and he watches the perimeter. Build defenses and he mans them while you sleep.

2. **You're never alone.** Krang is your operations officer. Eris is your uninvited roommate. They bicker, they help, they remember everything. The loneliest game ever made becomes a shared experience.

3. **Everything is earned.** No safe spaces. No hand-holding. You build your shelter, craft your terminal, install your cameras, construct your defenses. The AI support is the reward for good survival.

4. **Real-time apocalypse.** Your day is the game's day. Go to work. Come home. Krang tells you what happened. Your base either held or it didn't.

5. **Knowledge at your fingertips.** Ask Krang anything. Recipes, skill requirements, TV schedules, loot locations. He's the survival encyclopedia you'd kill to have in a real apocalypse.

6. **Your girlfriend gets the full experience.** Same world, same danger. Her own base, her own terminal, her own relationship with the AIs. Or share everything. Eris plays favorites and they both know it.
