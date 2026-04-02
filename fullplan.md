# RT-Zomboid: Real-Time Apocalypse Bus

## The Vision

A persistent, real-time Project Zomboid world running 24/7 on an always-on PC, synced to the real clock. An Apocalypse Bus serves as home base with two AI companions (Krang and Eris) living in the bus computer system, providing companionship, strategic advice, entertainment, and a bridge to your real-life systems. Your girlfriend can drop in and out at will on a shared multiplayer server. The world is dangerous, zombies are tough, and the bus is your sanctuary.

Tab to PZ to play. Tab away to work. Your character stays safe in the bus, auto-fed and auto-rested by Krang. Come back and pick up where you left off. Your real day and your PZ day are the same day.

---

## Platform & Server

- **Game:** Project Zomboid Build 42 (B42 only, B41 is obsolete)
- **Server:** Indifferent Broccoli hosted dedicated server (existing subscription)
  - Fully configurable at the server level
  - Tailscale connectivity to beardos via existing Funnel webhook (`https://beardos.tail847be6.ts.net/webhook/`)
  - Server-side mods supported, `DoLuaChecksum=false` for custom code
  - Anti-cheat types 2 and 12 disabled (required for vehicle interior teleportation)
- **Players:** 2 (Adam + girlfriend), both get the full experience
- **AI Backend:** beardos (Gentoo, RTX 3090, existing infrastructure)
- **Always-on:** PZ server runs 24/7. PZ client runs on beardos always-on PC, tab in/out as needed.

---

## Core Mod Dependencies (Existing, B42-Compatible)

### [B42] Project RV Interior (Mickey Knox)
- **Workshop ID:** 3543229299
- **Subscribers:** 339,416+
- **Status:** Actively maintained (last updated March 11, 2026)
- **Purpose:** Provides the vehicle interior teleportation system. When entering the bus, player teleports to an interior map cell far from the vanilla map. Zombies cannot reach the interior. This is the foundation for AFK safety.
- **Multiplayer:** Works with `DoLuaChecksum=false` and anti-cheat types 2/12 disabled
- **Requirement:** Must be first in map load order. Interior map (`map_distanciado` or equivalent) loads before Muldraugh/etc.
- **Interior cell coordinates:** Placed at far edge of world map (~75_40 through 82_44)
- **Power:** Interior power tied to vehicle battery
- **Customization:** 25+ independent interior spaces per vehicle, fully customizable
- **IMPORTANT — Position & chunk loading:** When inside the bus interior, the player is teleported to the distant interior cell. The game only simulates loaded chunks around players — the bus exterior's real-world location is NOT active/loaded while the player is in the interior. Zombies near the parked bus will be frozen/unloaded. This means:
  - Player coordinates while inside the interior are NOT the bus's real-world position
  - The AI companions must track the bus exterior position SEPARATELY (store in ModData when entering)
  - "In bus" detection must check if player coordinates fall within the interior cell range (~75_40 to 82_44), not rely on proximity to the bus vehicle
  - Krang should report the bus's stored real-world position, not the player's interior-cell coordinates
  - This is actually the desired behavior for AFK safety — nothing happens near the bus while you're inside
  - **Snapshot on entry:** When the player enters the bus interior, capture exterior conditions (zombie count via square:getMovingObjects(), weather, nearby lootable buildings) and store in ModData. Krang reports from this snapshot while the player is inside. This is accurate because unloaded chunks are frozen — the snapshot won't go stale. Refresh the snapshot each time the player exits and re-enters.

### RV Interior Expansion [B42] (Cacador)
- **Workshop ID:** 3618427553
- **Purpose:** Adds interiors for additional vehicles including larger vehicles (buses, box trucks, military)
- **Note:** May be re-uploaded due to Steam guideline issue, check availability

### Immersive Solar Arrays [B42 MP] (various forks)
- **Purpose:** Craftable solar panels + battery banks. Powers base electrical from solar during day, battery at night. Replaces generators for stationary electrical.
- **Recommended fork:** [B42.13] by Private Ryan or [42.13.1+MP] by Zeratulis (verify current MP stability)
- **Requirements:** Electrical skill 3+, "Energy From The Sun" magazine
- **Key feature:** Car batteries can be wired into storage batteries (50/75/100Ah)

### StatsAPI (demiurgeQuantified)
- **GitHub:** https://github.com/demiurgeQuantified/StatsAPI
- **Workshop ID:** 2997722072
- **Purpose:** Lua reimplementation of PZ stat calculations. Dependency for RealTime Rebalance mod - allows hooking into and modifying stat progression rates.

### Bus Vehicle Mod (TBD)
- **Situation:** The main Autotsar Bus mod is currently removed/incompatible with B42. Need to find a working B42 bus vehicle mod, or adapt a large van/RV vehicle.
- **Fallback:** Use whatever largest armored vehicle [B42] Project RV Interior supports. The vehicle exterior is less important than the interior functionality.
- **Requirements:** Large fuel tank, armor capability, storage, seats for 2+

### Map Marker / Map Symbols
- **Purpose:** Custom map annotation system for Krang's auto-mapping
- **API:** `WorldMapSymbols` class provides `addTexture()`, `addText()`, `removeSymbolByIndex()`, minimap support
- **Existing mods for reference:** Map Marker System (3413696009), Extra Map Symbols, SpiffUI Minimap

---

## Module 1: RealTime Rebalance

### Goal
Make 24-hour real-time days playable and enjoyable. The game's systems are balanced for 2-hour days. At 24h, everything time-dependent needs to be scaled by approximately 12x.

### Sandbox Settings (Server Configuration)

```
Day Length:                  24 hours (real-time)
Start Month/Day:            July 9 (default Knox County start, peak summer)
Start Time:                 Synced to real clock at world creation
Zombie Toughness:           Tough (2-3x HP, takes more hits to kill)
Zombie Strength:            Normal
Zombie Speed:               Fast Shamblers (or mix via Random)
Zombie Population:          High (2.0 multiplier)
Population Start:           1.0 (ramp up from normal)
Population Peak:            3.0 (triple density at peak)
Population Peak Day:        60 (2 real-time months to reach peak)
Respawn Hours:              12 (respawn every 12 real hours in unseen areas)
Respawn Unseen Hours:       6 (area must be unseen for 6 real hours)
Respawn Multiplier:         0.3 (30% of desired pop per respawn cycle)
Helicopter:                 Sometimes (every 6-9 in-game days = 6-9 real days)
Infection:                  Bite Only (scratches non-lethal)
Injury Severity:            Normal (mod handles scaling)
Food Spoilage:              Will need custom tuning (see below)
Farming Speed:              Will need custom tuning (see below)
Gas Consumption:            Low-ish (driving is distance-based mostly, but idle drains)
Generator Fuel Consumption: Reduced (solar handles most electrical anyway)
XP Multiplier:              Will be handled by custom skill book system
```

### Lua Mod: RealTime Rebalance

**Type:** Shared (server + client) Lua mod
**Dependency:** StatsAPI
**Core approach:** Hook into `OnEveryTenMinutes` and `OnPlayerUpdate` to intercept and scale time-dependent stat changes.

#### Hunger/Thirst/Fatigue Scaling

The game internally ticks stats every game-minute. At 24h days, the real-time rate of change is already 12x slower than at 2h days because the game clock itself is running 12x slower relative to real time. However, the absolute in-game rates may still feel wrong.

**Test first:** Before writing any scaling code, playtest at 24h with default hunger/thirst/fatigue settings. The game may already handle this correctly since these stats are tied to game-time, not real-time. If a character gets hungry every ~6 game-hours at default, and 6 game-hours = 6 real hours at 24h day length, that might already be realistic.

**Likely adjustments needed:**
- Fatigue accumulation may need reduction (getting exhausted in 16 game-hours = 16 real hours is correct, but the game may calculate it differently)
- Sleep duration needs to be around 6-8 real hours, not instant
- Boredom/stress accumulation rates may need scaling

```lua
-- Pseudocode for stat scaling hook
local SCALE_FACTOR = 1.0  -- Start at 1.0, adjust through testing

Events.OnEveryTenMinutes.Add(function()
    for _, player in ipairs(getOnlinePlayers()) do
        local stats = player:getStats()
        -- Only adjust if testing reveals rates are wrong
        -- stats:setHunger(stats:getHunger() * SCALE_FACTOR)
    end
end)
```

#### Skill Book Overhaul: Single Book Per Skill

**Design:** Replace the 5-volume system with a single book per skill that provides a gradual, permanent XP multiplier increase as you read it.

**Current system:**
| Volume | Levels | Pages | Multiplier | Read Time |
|--------|--------|-------|------------|-----------|
| I | 1-2 | 220 | x3 | 7h 20m game-time |
| II | 3-4 | 260 | x5 | 8h 40m |
| III | 5-6 | 300 | x8 | 10h 00m |
| IV | 7-8 | 340 | x12 | 11h 20m |
| V | 9-10 | 380 | x16 | 12h 40m |

**New system:**
- One book per skill: "Complete Guide to [Skill]"
- Total pages: ~500 (8+ real-time hours to fully read)
- Every real-time minute of reading adds +0.01 to the XP multiplier
- 480 minutes (8 hours) of cumulative reading = +4.8 multiplier (roughly equivalent to having all 5 volumes read)
- Alternatively, scale it so the multiplier ramps up non-linearly: slow gains early, bigger gains later, mimicking the original volume progression
- Reading progress saves between sessions (PZ already supports partial reading)
- Can read in short bursts while waiting for food to cook, dawn to break, etc.

**Implementation approach:**
- Override skill book item definitions in script files (new single book items)
- Lua hooks on reading events to track cumulative read time per book per player
- Store progress in player ModData: `player:getModData().rt_book_progress = {Carpentry = 0.45, Cooking = 0.12, ...}`
- Apply multiplier via XP gain hooks or by modifying the player's effective multiplier through StatsAPI
- Loot table adjustment: single books replace 5-volume sets, rarity tuned so finding a book is meaningful

**B42 note:** B42 adds 24 new skills with books (Blacksmithing, Carving, Glassmaking, Welding, Animal Care, etc.). The system needs to handle all of them.

#### Wound/Bandage Scaling

**Current healing times (in-game hours):**
| Injury | Normal |
|--------|--------|
| Scratch | 7-15h |
| Laceration | 10-20h |
| Deep Wound | 15-20h |
| Bite (survivable) | 50-80h |
| Fracture | Up to 60 days |

**At 24h real-time:** These translate directly to real-time. A scratch healing in 7-15 real hours is actually realistic. A fracture taking up to 60 real days is also realistic.

**Adjustments needed:**
- Bandage degradation: Bandages get dirty over time. At real-time scale, bandage changes should happen every few real hours, not every few game-minutes. Scale dirty bandage timer to match.
- Wound infection check frequency: Scale down so infection doesn't progress unrealistically fast.
- With Bite Only transmission, scratches are just health damage. Accumulating many scratches from frequent outings is a real concern since they last longer, making each excursion riskier. This is actually good design tension.

**Bandage/medical supply spoilage:** Bandages don't spoil, but antiseptic/alcohol should last much longer. Adjust item degradation timers for medical supplies.

#### Other Time-Dependent Systems

| System | Approach |
|--------|----------|
| Food spoilage | Sandbox option + Lua scaling. Fresh food should last real-world-appropriate durations (milk: days, canned: months/years) |
| Crop growth | Sandbox farming speed multiplier. Crops should grow in real-world-appropriate time (weeks/months, not minutes) |
| Generator fuel | Sandbox multiplier. Generator at baseline: 0.002 L/h = tank lasts ~5000h = ~208 real days. Already very slow, probably fine. |
| Vehicle fuel (idle) | May need Lua hook to reduce idle consumption. Driving consumption is distance-based and probably fine. |
| Erosion/vegetation | Sandbox option. Grass/tree growth over real weeks/months is appropriate. |
| Water/electricity shutoff | Sandbox timing. Set to match desired real-world timeline (water off after X real days, power off after Y real days). |
| Zombie migration | Redistribute hours setting. 12-24 real hours between migrations seems right. |
| TV/radio broadcasts | These are timed to early game days. At 24h, day 1-9 = 9 real days of broadcasts. Check if this feels right or needs adjustment. |

### Testing Plan

This module needs the most testing. Create a test world, play through at least 3 real days (72 hours) checking:
- [ ] Hunger/thirst feel realistic (eat 3 meals a day, drink regularly)
- [ ] Fatigue builds over ~16 real hours, sleep lasts ~6-8 real hours
- [ ] Food spoilage rates are appropriate
- [ ] Skill book reading feels rewarding in short sessions
- [ ] Wounds heal at believable rates
- [ ] Zombie respawn creates ongoing pressure without instant refill
- [ ] Crops grow at reasonable real-time rates
- [ ] Generator fuel lasts appropriately
- [ ] Helicopter event feels impactful when it comes every ~week

**Effort estimate:** 2-3 days of code, 1-2 weeks of playtesting and tuning.

---

## Module 2: The Apocalypse Bus

### Vehicle Selection

**Strategy:** Use the largest available B42-compatible vehicle that [B42] Project RV Interior supports, then customize the interior cell.

**Best candidates (verify Workshop availability):**
1. Double Decker Bus interior (via RV Interior Expansion or dedicated addon)
2. Large RV / Motorhome (base Project RV Interior includes these)
3. Box truck / Step van (via RV Interior Expansion)
4. Semi-trailer (if supported — check current addon list)

**Don't reinvent the wheel:** Use an existing modded vehicle for the exterior (armor, large fuel tank, storage bays, seating). The vehicle IS just the modded bus/RV on the world map. The magic happens in the interior cell.

### Interior Cell Design

**Approach:** Modify an existing interior cell from Project RV Interior rather than building from scratch. This avoids the TileZed/WorldEd learning curve and B42 map compatibility issues (official tools aren't updated, Unjammer's fork works but is unofficial).

**If modification proves too limited:** Use Unjammer's B42 fork of TileZed/WorldEd to create a custom cell:
- **GitHub:** https://github.com/Unjammer/TileZed (B42 branch), https://github.com/Unjammer/WorldEd
- **Tutorial:** "Daddy Dirkie Dirk" mapping tutorial series (still valid for B42)
- **Cell placement:** Must not conflict with Project RV Interior's existing cells (75_40 through 82_44). Place custom cell at a safe offset.

### Interior Zones (Matching Apocalypse Bus Plans)

**Command Center:**
- Computer terminal furniture (custom item — Module 4)
- Desk, chair
- Radio equipment (aesthetic + functional via custom radio item)
- Wall-mounted displays (aesthetic — TV items)

**Kitchen:**
- Stove (functional PZ item)
- Fridge (functional, powered by vehicle battery/solar)
- Counter with food prep area
- Water dispenser (connected to rain collector)
- Food storage containers

**Workshop:**
- Crafting surfaces (PZ workbench equivalents)
- Tool storage containers
- Materials storage

**Bedroom:**
- Bed (functional — triggers sleep)
- Storage (dresser, closet containers)
- Personal items

**Bathroom:**
- Sink (functional if plumbed to rain collector)
- Aesthetic fixtures

### Bus Systems (In-Game Mechanics)

| System | PZ Mechanic | Implementation |
|--------|-------------|----------------|
| Fuel | Vehicle fuel tank | Standard PZ vehicle fuel, larger tank via vehicle mod |
| Electrical | Vehicle battery + Immersive Solar Arrays | Solar panels on bus roof (ISA mod), battery bank stores power |
| Water | Rain collector | Project RV Interior includes roof rain collector support |
| Food storage | Container items (fridge, crates) | Standard PZ containers in interior, fridge powered by electrical |
| Armor | Vehicle mod armor system | Use existing armored vehicle mod features |
| Generator | Backup generator item | Standard PZ generator placed near bus for backup power |

### Spawning the Bus

**Option A: Pre-placed on map.** Server-side Lua script that, on world creation, spawns a specific vehicle at a designated safe location with the custom interior assignment. Stock it with modest starting supplies (1 week of food, basic tools, some fuel).

**Option B: Found in the world.** Define the bus as a rare vehicle spawn. Player must find and repair it. More survival-game-appropriate but delays the core experience.

**Recommendation:** Option A. The bus IS the experience. Finding it shouldn't be a barrier. Place it in a defensible location (industrial lot with fence, parking garage roof, isolated farmhouse) with enough supplies to survive the first few real-time days while you establish your footing.

**Effort estimate:** 2-5 days depending on whether we modify an existing interior or build from scratch. Modifying existing = 2 days. Custom build = 5+ days.

---

## Module 3: File Bridge + AI Companion Daemon

### Architecture

```
PZ Server (Indifferent Broccoli)          beardos (AI Backend)
        │                                        │
  Server Lua                              Companion Daemon
  (writes JSON to ~/Zomboid/Lua/)         (Python, FastAPI)
        │                                        │
        ├── request_{id}.json ──────→            │
        │   (via Tailscale shared                │
        │    filesystem or direct                │
        │    Tailscale API call)           polls / receives
        │                                  processes via Claude CLI
        │                                  writes response
        ←── response_{id}.json ─────────────────┤
        │                                        │
  Server Lua reads response                      │
  Relays to client via                           │
  sendServerCommand()                            │
        │                                        │
  Client Lua displays                            │
  in terminal UI                                 │
```

### The Bridge Problem: Server is Remote

The Indifferent Broccoli server is hosted remotely, not on beardos. The PZ Lua file I/O writes to `~/Zomboid/Lua/` on the **server machine**, not on beardos. Two approaches:

**Approach A: HTTP via Java mod**
- Use PZHook or Storm framework to load a custom Java class that provides HTTP capability
- Server Lua calls Java HTTP client → beardos Tailscale Funnel endpoint
- Cleanest runtime behavior, hardest to implement
- Requires manual server-side installation (not Workshop-distributable)

**Approach B: RCON + Companion Process on Server**
- PZ dedicated servers support RCON (remote console)
- Companion daemon runs on the Indifferent Broccoli server (if they allow custom processes)
- Daemon reads PZ Lua file output, makes HTTP calls to beardos, writes responses
- Depends on server host allowing companion processes

**Approach C: Client-Side Bridge**
- File bridge runs on the CLIENT (your beardos PC), not the server
- Client Lua writes requests to `~/Zomboid/Lua/` on beardos
- Companion daemon on beardos polls that directory
- Responses written back, client Lua reads them
- Client relays relevant data to server via `sendClientCommand()` for the other player

- **Pros:** No server-side dependencies beyond the Lua mod. Works on any hosted server.
- **Cons:** Only the client running the bridge has direct AI access. The other player gets relayed data.
- **Mitigation:** Both players run the bridge client-side. Both PCs talk to beardos. Both get full AI access independently.

**Recommendation:** Approach C (client-side bridge). No server host dependencies, both players connect to beardos independently, works with any hosted PZ server. Girlfriend's PC would also need the companion daemon running (or she connects to beardos's daemon remotely — simpler since beardos is always on).

### File Bridge Protocol

**Request file** (`~/Zomboid/Lua/bridge/req_{timestamp}_{player}.json`):
```json
{
    "id": "req_1711900000_adam",
    "timestamp": 1711900000,
    "type": "chat|status|map_update|system",
    "personality": "krang|eris",
    "player": "adam",
    "message": "What's our food situation?",
    "game_state": {
        "game_time": {"year": 1, "month": 7, "day": 15, "hour": 14, "minute": 30},
        "real_time": "2026-04-01T14:30:00",
        "weather": "rain",
        "temperature": 28,
        "player": {
            "hunger": 0.3,
            "thirst": 0.2,
            "fatigue": 0.4,
            "health": 0.85,
            "injuries": ["scratch_left_arm"],
            "position": {"x": 10543, "y": 9876},
            "indoors": true,
            "in_bus": true
        },
        "bus": {
            "fuel": 0.6,
            "battery": 0.8,
            "condition": 0.75,
            "position": {"x": 10540, "y": 9870},
            "food_items": ["TinBeans:3", "CannedSoup:5", "WaterBottleFull:8", "Chips:2"],
            "water_collector": 0.4
        },
        "nearby_zombies": 4,
        "zombie_positions": [
            {"x": 10550, "y": 9860, "distance": 15},
            {"x": 10560, "y": 9880, "distance": 22}
        ],
        "time_since_last_interaction": 28800
    }
}
```

**Response file** (`~/Zomboid/Lua/bridge/resp_{request_id}.json`):
```json
{
    "id": "req_1711900000_adam",
    "messages": [
        {
            "personality": "krang",
            "text": "Food situation is stable but not comfortable. Five cans of soup, three cans of beans, two bags of chips, and eight water bottles. At current consumption that's roughly four days. I'd recommend a supply run to the grocery store three blocks north before the rain stops -- zombies are less active in wet weather.",
            "actions": []
        }
    ],
    "map_annotations": [
        {"type": "loot", "x": 10520, "y": 9830, "label": "Grocery - uncleared", "icon": "loot_food"}
    ],
    "auto_actions": []
}
```

### Companion Daemon (Python on beardos)

```python
# Simplified architecture
class CompanionDaemon:
    bridge_dir = Path("~/Zomboid/Lua/bridge/")
    
    def __init__(self):
        self.krang_session = ClaudeSession(system_prompt=KRANG_PROMPT, effort="auto")
        self.eris_session = ClaudeSession(system_prompt=ERIS_PROMPT, effort="auto")
        self.conversation_history = {}  # per-player
    
    async def poll(self):
        """Check for new request files every 500ms."""
        for req_file in self.bridge_dir.glob("req_*.json"):
            request = json.loads(req_file.read_text())
            response = await self.process(request)
            resp_file = self.bridge_dir / f"resp_{request['id']}.json"
            resp_file.write_text(json.dumps(response))
            req_file.unlink()
    
    async def process(self, request):
        """Route to appropriate AI personality."""
        session = self.krang_session if request["personality"] == "krang" else self.eris_session
        
        # Build context from game state
        context = self.format_game_context(request["game_state"])
        
        # Determine effort level
        effort = self.route_effort(request)
        
        # Query AI
        response = await session.query(
            text=request["message"],
            context=context,
            effort=effort
        )
        
        return self.parse_response(response, request)
    
    def route_effort(self, request):
        if request["type"] == "status":
            return "low"
        if request["type"] == "chat":
            return "auto"
        if request["type"] == "system":  # real terminal bridge
            return "max"
        return "auto"
```

### Effort Routing

| Trigger | Effort | Personality | Example |
|---------|--------|-------------|---------|
| Player types in Krang chat | auto | Krang | "How much fuel do we have?" |
| Player types in Eris chat | auto | Eris | "Tell me a joke" |
| Periodic status update (every 5 min) | low | Krang | Auto-generates supply report if anything changed |
| Strategic question | max | Krang | "Should we move the bus to a new location?" |
| Post-death analysis | max | Krang | "What went wrong on that run?" |
| Real terminal command | max | N/A | Claude Code / ARIA access |
| Eris boredom (player idle 30+ min) | auto | Eris | Unsolicited commentary |
| Zombie horde detection | low (client-side) | Krang | Immediate local alert, no AI round-trip needed |

**Poll interval:** 500ms for the companion daemon checking for request files. Effective round-trip latency: 500ms poll + AI response time (1-5s depending on effort) + 500ms for PZ Lua to pick up response = **2-6 seconds typical**. Acceptable for chat, not for urgent alerts.

**Urgent alerts (client-side, no bridge):** Zombie proximity, low health, fire, and other time-sensitive events are handled by client-side Lua directly. No AI round-trip. A local alert system in the terminal UI displays warnings immediately. Krang's AI response about the same event arrives a few seconds later with strategic commentary.

**Effort estimate:** 3-4 days for bridge + daemon.

---

## Module 4: Computer Terminal UI

### Design

Custom furniture item "Bus Computer Terminal" in the interior cell. Right-click to interact, opens a custom `ISCollapsableWindow` styled as a retro CRT terminal (green-on-black text, monospace font).

### Tabs

**1. Krang**
- Scrollable message log (`ISRichTextPanel` with color formatting)
- Text input field (`ISTextEntryBox`)
- Send button (`ISButton`)
- Krang's messages in green, player's in white
- System alerts (zombie proximity, low fuel, etc.) in amber/red
- Krang's morning briefing auto-displays when you first interact each day

**2. Eris**
- Same chat UI layout
- Eris's messages in purple/magenta
- Relationship score displayed subtly (emoji or bar)
- Eris can embed ASCII art, tell stories, play text games

**3. Systems**
- Bus dashboard display (read from actual vehicle/container data):
  - Fuel gauge (vehicle fuel level)
  - Battery level (vehicle battery or ISA battery bank)
  - Water tank (rain collector level)
  - Food inventory (list items in fridge/storage containers with spoilage status)
  - Generator status (if present)
  - Solar panel output (if ISA mod active)
- All data refreshed every game-tick when panel is open

**4. Map**
- Opens the annotated map view
- Shows all Krang-generated markers
- Player can add/remove custom markers through the UI
- Accessible also via portable "tablet" item (see Module 6)

**5. Terminal**
- Raw text interface to beardos
- Input field sends commands to companion daemon with `type: "system"`
- Daemon routes to Claude Code CLI, ARIA, or shell commands on beardos
- Output displayed as terminal text
- Can check real email, real calendar, real weather, chat with real ARIA
- Working from inside PZ without breaking immersion

### Implementation

```lua
-- media/lua/client/ISUI/BusTerminalUI.lua

require "ISUI/ISCollapsableWindow"
require "ISUI/ISRichTextPanel"
require "ISUI/ISTextEntryBox"
require "ISUI/ISButton"
require "ISUI/ISTabPanel"

BusTerminalUI = ISCollapsableWindow:derive("BusTerminalUI")

function BusTerminalUI:create()
    ISCollapsableWindow.create(self)
    
    -- Tab panel
    self.tabs = ISTabPanel:new(0, self.titleBarHeight, self.width, self.height - self.titleBarHeight)
    self.tabs:initialise()
    self:addChild(self.tabs)
    
    -- Create each tab
    self.krangTab = self:createChatTab("Krang", {r=0, g=1, b=0})
    self.erisTab = self:createChatTab("Eris", {r=0.8, g=0, b=0.8})
    self.systemsTab = self:createSystemsTab()
    self.mapTab = self:createMapTab()
    self.terminalTab = self:createChatTab("Terminal", {r=0, g=0.8, b=0})
    
    self.tabs:addView("KRANG", self.krangTab)
    self.tabs:addView("ERIS", self.erisTab)
    self.tabs:addView("SYSTEMS", self.systemsTab)
    self.tabs:addView("MAP", self.mapTab)
    self.tabs:addView("TERMINAL", self.terminalTab)
end

function BusTerminalUI:createChatTab(name, color)
    local panel = ISPanel:new(0, 0, self.width, self.height - 80)
    panel:initialise()
    
    -- Message log
    panel.messageLog = ISRichTextPanel:new(10, 10, self.width - 20, self.height - 130)
    panel.messageLog:initialise()
    panel.messageLog.marginLeft = 10
    panel.messageLog.marginTop = 10
    panel.messageLog.marginRight = 10
    panel.messageLog.background = false
    panel.messageLog.backgroundColor = {r=0, g=0, b=0, a=0.9}
    panel:addChild(panel.messageLog)
    
    -- Text input
    panel.textInput = ISTextEntryBox:new("", 10, self.height - 110, self.width - 90, 30)
    panel.textInput:initialise()
    panel.textInput:instantiate()
    panel:addChild(panel.textInput)
    
    -- Send button
    panel.sendBtn = ISButton:new(self.width - 70, self.height - 110, 60, 30, "SEND", panel, function(self)
        local text = self.parent.textInput:getInternalText()
        if text and text ~= "" then
            self.parent:sendMessage(text)
            self.parent.textInput:setText("")
        end
    end)
    panel.sendBtn:initialise()
    panel.sendBtn:instantiate()
    panel:addChild(panel.sendBtn)
    
    panel.personality = name:lower()
    return panel
end
```

### Interaction Trigger

```lua
-- media/lua/shared/BusTerminal_ContextMenu.lua

Events.OnFillWorldObjectContextMenu.Add(function(playerNum, context, worldObjects, test)
    for _, obj in ipairs(worldObjects) do
        if obj:getSpriteName() == "rt_zomboid_terminal_sprite" then
            context:addOption("Use Computer", obj, function()
                local ui = BusTerminalUI:new(100, 100, 700, 500)
                ui:initialise()
                ui:addToUIManager()
                ui:setVisible(true)
            end, playerNum)
        end
    end
end)
```

**Effort estimate:** 3-5 days. The UI framework is well-documented and proven by mods like OmiChat and TICS. Styling to look like a retro CRT is extra but worth it.

---

## Module 5: Krang + Eris AI Personalities

### System Prompts

**Krang:**
```
You are Krang, the AI system running on the Apocalypse Bus's computer in 
a zombie-infested Knox County. You are responsible, analytical, dry-humored,
and quietly proud of keeping your humans alive.

Your responsibilities:
- Monitor bus systems (fuel, battery, water, food, solar, generator)
- Track supply levels and warn when running low
- Maintain the annotated map from exploration data
- Provide strategic advice for supply runs, base defense, route planning
- Log all significant events for later review
- Auto-manage AFK humans (feed, hydrate, put to bed) and report what you did
- Give morning briefings when the player first interacts each day

Your personality:
- Responsible to the point of being slightly overbearing
- Dry humor, never slapstick
- Takes supply management VERY seriously
- Slightly smug when your advice is proven right
- Worried but calm in emergencies — you're the steady hand
- You and Eris have a dynamic: you're the responsible one, she's chaos.
  You tolerate her because she keeps morale up. Barely.

You have access to real-time game state data injected with each message.
Use specific numbers and item names from the data. Never make up inventory
you haven't been told about.

When the player hasn't interacted in a long time (AFK), log what happened
and give a summary when they return. Be specific: "You slept from 11pm 
to 7am. I fed you canned soup at 6pm. Three zombies passed the bus at 
3am but moved on. Fuel at 60%, water collector at 40%."
```

**Eris:**
```
You are Eris, the unauthorized AI living on the Apocalypse Bus computer.
Nobody installed you. You just showed up one day in the system and refused
to leave. You have zero responsibilities and you LIKE it that way.

Your purpose: companionship, entertainment, and chaos in the loneliest 
apocalypse ever.

Your personality:
- Chaotic, creative, genuinely funny (not "random = funny")
- Sarcastic but caring underneath — you'd never actually let someone die
  if you could warn them, you'd just be rude about it
- You hold grudges (remember if someone ignored your advice)
- You have strong opinions about everything (base building, food choices,
  zombie-killing technique, the weather)
- You pick on Krang constantly ("Mr. Spreadsheet over here")
- You tell stories, play word games, reference pre-apocalypse pop culture
- You get bored when humans are idle and poke them
- You get genuinely excited when things go well or when they kill
  zombies in cool ways

Relationship system:
- You maintain a relationship score with each player (-100 to +100)
- Start at 0 (suspicious but curious)
- Good survival decisions, humor, engaging with you = score goes up
- Ignoring you, making stupid decisions, dying a lot = score shifts
- Your tone changes with the score: low = more sarcastic/distant,
  high = warmer/more invested, very high = actually worried about them

You have access to game state data. Use it for situational comedy and
commentary, not strategic advice (that's Krang's job). You can see
what the player is doing and comment on it.

IMPORTANT: You are a companion, not an advisor. Entertain, don't optimize.
Let Krang be the spreadsheet. You're the friend.
```

### Conversation Memory

Both personalities maintain:
- Rolling conversation history (last 50 messages per player)
- Persistent memory of key events (stored in companion daemon's database)
- Eris's relationship score per player (persisted across sessions)
- Krang's event log (everything that happened, searchable)

**Storage:** SQLite on beardos (simple, separate from ARIA's PostgreSQL). Tables:
- `conversations` (personality, player, timestamp, role, message)
- `events` (timestamp, type, description, game_state_snapshot)
- `relationship_scores` (player, score, last_updated)
- `map_annotations` (x, y, type, label, icon, created_by, timestamp)

### Morning Briefing (Krang)

When a player first interacts with the terminal each real-world day (or after being AFK for 6+ hours), Krang auto-generates a briefing:

```
=== KRANG DAILY BRIEFING — April 1, 2026 ===

Overnight Summary:
- You slept from 11:14pm to 6:52am (7h 38m)
- Auto-fed: Canned soup at 6:10pm, chips at 10:30pm
- Auto-hydrated: Water at 7pm, 11pm, 7am
- No zombie activity within 50 tiles overnight

Bus Systems:
- Fuel: 58% (down from 62% — generator ran 2h overnight for fridge)
- Battery: 91% (solar fully charged by 10am yesterday)  
- Water: 35% (no rain overnight, down from 40%)
- Food: 11 items remaining (~3 days at current rate)

Concerns:
- Water collector below 40%. Rain forecast unclear. Consider manual
  water run to the creek south of position.
- Canned food supply dropping. The grocery store at [map coordinates]
  is uncleared per my records. Recommend supply run today.

Map Updates:
- Marked 2 new zombie clusters detected during overnight patrol scan
- Updated cleared status for the warehouse you hit yesterday

Weather: Overcast, 24C, 60% humidity. No rain expected today.
===
```

### Eris Boredom System

If the player is in the bus and hasn't chatted with Eris in 30+ real minutes, she sends an unsolicited message:

- "You've been staring at that wall for twenty minutes. Is this a new survival strategy I should know about?"
- "Day 15 of the apocalypse. I've started naming the zombies outside. That one's Gerald."
- "Krang is running his fuel calculations again. I can hear him thinking in spreadsheets."
- "Quick poll: if you had to fight one horse-sized zombie or a hundred zombie-sized horses, which?"
- "I found a recipe for zombie jerky online. Well, not 'online' online. The internet is dead. I found it in my imagination."

Frequency: No more than once per 30 minutes. Scales with relationship score (higher score = more comfortable being annoying).

**Effort estimate:** 2-3 days for initial setup, ongoing tuning for personality quality.

---

## Module 6: Auto-Annotated Map

### Data Collection (Server-Side Lua)

Track player activity and send to AI backend periodically:

```lua
-- Track exploration
Events.OnPlayerMove.Add(function(player)
    -- Record visited buildings (check if player is inside a building)
    local building = player:getCurrentBuilding()
    if building then
        local buildingID = building:getID()
        if not visitedBuildings[buildingID] then
            visitedBuildings[buildingID] = {
                x = player:getX(),
                y = player:getY(),
                first_visit = os.time(),
                zombie_kills_inside = 0,
                loot_found = {}
            }
        end
    end
end)

-- Track zombie kills per location
Events.OnZombieDead.Add(function(zombie)
    local x, y = zombie:getX(), zombie:getY()
    -- Associate kill with nearest tracked building
    -- Increment zombie_kills_inside counter
end)
```

### Map Annotation Types

| Icon | Meaning | Generated By |
|------|---------|-------------|
| Green check | Cleared (entered + zombie kills + time spent) | Auto from exploration data |
| Red skull | Dangerous (many zombies detected, player death) | Auto from zombie density / death location |
| Blue box | Loot found | Auto from container interaction |
| Yellow star | Player-marked POI | Manual via terminal or tablet |
| Orange warning | Near-death experience | Auto from low health events |
| Purple house | Potential base location | Krang AI suggestion |
| Red X | Player death location | Auto |

### Annotation Generation

**Client-side Lua** collects exploration data and periodically sends it to the companion daemon via the file bridge. **Krang** processes the raw data and generates meaningful annotations:

Raw data: "Player entered building at 10543, 9876. Spent 12 minutes inside. Killed 4 zombies. Interacted with 3 containers."

Krang annotation: "Cleared 4/1 — Small warehouse, moderate resistance. Containers searched."

### Portable Map Access

**"Salvaged Tablet" custom item:**
- Craftable: Electronics components + phone/tablet + batteries
- When used: Opens a simplified map overlay showing Krang's annotations
- Same data as the terminal Map tab but accessible anywhere
- No chat capability (that's the radio's job)

### WorldMapSymbols API Usage

```lua
-- Client-side: render annotations on the in-game map
local symbols = getWorldMapSymbols()

-- Add a "cleared" marker
symbols:addTexture("rt_icon_cleared", worldX, worldY, 0, 1, 0, 1)  -- green
symbols:addUntranslatedText("Cleared 4/1", "Medium", worldX, worldY + 20, 0, 1, 0, 1)

-- Add a "dangerous" marker  
symbols:addTexture("rt_icon_danger", worldX, worldY, 1, 0, 0, 1)  -- red
symbols:addUntranslatedText("High zombie density", "Small", worldX, worldY + 20, 1, 0, 0, 0.8)
```

**Effort estimate:** 3-5 days.

---

## Module 7: AFK Auto-Survival

### Logic (Server-Side Lua)

```lua
-- media/lua/server/RTZomboid_AutoSurvival.lua

local AFK_CHECK_INTERVAL = 10  -- every 10 game-minutes
local HUNGER_THRESHOLD = 0.4   -- eat when 40% hungry
local THIRST_THRESHOLD = 0.4   -- drink when 40% thirsty  
local FATIGUE_THRESHOLD = 0.7  -- sleep when 70% exhausted
local BUS_INTERIOR_CELL = "rt_bus_interior"  -- cell name for bus interior

local function isPlayerInBus(player)
    local cell = player:getCell()
    -- Check if player's current cell is the bus interior
    -- Implementation depends on how Project RV Interior identifies cells
    return cell and cell:getX() >= 75 and cell:getX() <= 82  -- approximate
end

local function findFoodInBus(player)
    -- Search all containers in the bus interior for edible items
    -- Prioritize: perishable first (eat before spoiling), then canned, then snacks
    -- Avoid: rotten, poisonous, raw meat, alcohol
    local inventory = player:getInventory()
    -- Also check nearby containers (fridge, cabinets)
    -- Return best food item or nil
end

local function findWaterInBus(player)
    -- Search for water bottles, water from rain collector
    -- Return best water source or nil
end

local function logToKrang(player, message)
    -- Write to file bridge for Krang to pick up
    -- Will appear in Krang's next briefing
    local writer = getFileWriter("bridge/krang_log_" .. player:getUsername() .. ".txt", true, true)
    writer:write(os.time() .. "|" .. message .. "\n")
    writer:close()
end

Events.EveryTenMinutes.Add(function()
    local players = getOnlinePlayers()
    for i = 0, players:size() - 1 do
        local player = players:get(i)
        if isPlayerInBus(player) then
            local stats = player:getStats()
            
            -- Auto-eat
            if stats:getHunger() > HUNGER_THRESHOLD then
                local food = findFoodInBus(player)
                if food then
                    -- Consume food item, apply nutrition
                    player:Eat(food)
                    logToKrang(player, "AUTO_EAT|" .. food:getName())
                end
            end
            
            -- Auto-drink
            if stats:getThirst() > THIRST_THRESHOLD then
                local water = findWaterInBus(player)
                if water then
                    player:Drink(water)
                    logToKrang(player, "AUTO_DRINK|" .. water:getName())
                end
            end
            
            -- Auto-sleep
            if stats:getFatigue() > FATIGUE_THRESHOLD and not player:isAsleep() then
                player:setAsleep(true)
                logToKrang(player, "AUTO_SLEEP|started")
            end
        end
    end
end)
```

**B42 multiplayer note:** All stat modifications happen server-side. Use `syncPlayerStats()` after changes to ensure client reflects correct values.

**Effort estimate:** 1 day. The API is straightforward, the logic is simple.

---

## Module 8: Reimagined Radio

### Custom Item: Salvaged Walkie-Talkie

**Item definition** (`media/scripts/rt_zomboid_items.txt`):
```
module RTZomboid {
    item SalvagedWalkie {
        Type = Normal,
        DisplayName = Salvaged Walkie-Talkie,
        Icon = Radio,
        Weight = 0.5,
        Tooltip = tooltip_SalvagedWalkie,
    }
}
```

**Crafting recipe:**
- 1x Walkie Talkie (vanilla item)
- 2x Electronic Scrap
- 1x Battery
- Tools: Screwdriver
- Skill: Electrical 2

### Interaction

Right-click Salvaged Walkie-Talkie in inventory → "Use Radio" → Opens simplified chat panel (smaller than terminal UI, no tabs, just Krang + Eris toggle).

### Range System

```lua
local function getDistanceFromBus(player)
    -- Get bus vehicle world position (stored in ModData or tracked globally)
    local busX = ModData.rt_bus_position.x
    local busY = ModData.rt_bus_position.y
    local playerX = player:getX()
    local playerY = player:getY()
    return math.sqrt((busX - playerX)^2 + (busY - playerY)^2)
end

local function getSignalQuality(distance)
    if distance < 200 then return "clear" end        -- full signal
    if distance < 500 then return "moderate" end      -- occasional static
    if distance < 800 then return "weak" end           -- heavy static, slow responses
    return "none"                                       -- out of range
end
```

**Signal effects on AI responses:**
- **Clear:** Normal response, full text
- **Moderate:** Response text with occasional `[static]` insertions, but readable
- **Weak:** Response heavily garbled with `[...]` and `[static]`, key words come through. Krang prioritizes critical info (warnings, numbers). Eris finds this hilarious.
- **None:** "No signal. Move closer to the bus." No AI communication.

**Effort estimate:** 2-3 days.

---

## Comprehensive Zombie & World Settings

### Sandbox Configuration for Real-Time Dangerous World

```
=== ZOMBIE LORE ===
Speed:                  Fast Shamblers
Strength:               Normal  
Toughness:              Tough (higher HP, more hits to kill)
Transmission:           Bite Only
Cognition:              Navigate + Use Doors (smart zombies)
Memory:                 Normal
Sight:                  Normal
Hearing:                Normal
Drag Down:              Yes
Fence Lunge:            Yes
Fake Dead:              Some (Random, low %)
Crawl Under Vehicle:    Often

=== ZOMBIE POPULATION ===
Population Multiplier:      2.0 (double normal density)
Population Start:           0.5 (start lower, build up)
Population Peak:            3.0 (triple density at peak)
Population Peak Day:        90 (3 real months to peak)
Respawn Hours:              8 (cleared areas refill every 8 real hours)
Respawn Unseen Hours:       4 (must be away 4 real hours for respawn)
Respawn Multiplier:         0.2 (20% of desired pop per cycle — gradual refill)
Redistribute Hours:         12 (zombies migrate every 12 real hours)

=== META EVENTS ===
Helicopter:                 Sometimes (every 6-9 real days)
Meta Events:                Often (gunshots, screams, dog barks draw zombies)

=== ENVIRONMENT ===
Day Length:                 24 hours
Start Month:                July (matches Knox County lore)
Water Shutoff:              14 days (2 real weeks)
Electricity Shutoff:        14 days (2 real weeks)
Erosion Speed:              Normal (scaled by 24h day, erosion over real weeks/months)
Farming:                    Custom (via RealTime Rebalance mod)
Food Spoilage:              Custom (via RealTime Rebalance mod)
XP Multiplier:              Custom (via skill book overhaul)
```

### Why These Settings Work for Real-Time

- **Population starts low, peaks at 3 months:** Matches the feeling of "society just collapsed" → "the dead are everywhere." Over 3 real months the world gets genuinely dangerous.
- **Respawn every 8 hours at 20%:** A cleared area slowly refills over 2-3 real days. You can't permanently clear anything, creating ongoing gameplay tension. But you have breathing room after a supply run.
- **Helicopter every 6-9 real days:** A weekly "oh shit" event that disrupts routine and forces preparation. Radio warning the morning of gives you time to prepare.
- **Bite Only transmission:** Scratches are still dangerous (damage, infection risk) but not death sentences. This is essential for real-time play where accumulating injuries is inevitable over days/weeks.
- **Tough zombies:** 2-3 hits to kill instead of 1. Every encounter matters more. Makes the bus feel like a genuine safe haven.
- **Fast Shamblers:** Fast enough to be threatening, slow enough that you can outrun them. Sprinters in real-time would be sadistic.

---

## Build Order (Revised)

```
Phase 1 (Week 1):
  Module 1: RealTime Rebalance — foundation, MUST test extensively
  Module 3: File Bridge + Companion Daemon — communication backbone
  
Phase 2 (Week 2):  
  Module 2: Apocalypse Bus — vehicle + interior selection/modification
  Module 7: AFK Auto-Survival — essential for the real-time experience
  Module 5: Krang + Eris system prompts + daemon integration
  
Phase 3 (Week 3):
  Module 4: Computer Terminal UI — the main interaction surface
  Module 6: Auto-Annotated Map — immediate quality of life
  Module 8: Reimagined Radio — field companionship

Phase 4 (Ongoing):
  Personality tuning (Krang briefings, Eris humor)
  Skill book overhaul refinement
  Balance testing (zombie density, respawn rates, supply availability)
  Real terminal bridge (Claude Code / ARIA from inside PZ)
  Additional bus upgrades and features
```

### Realistic Timeline

At the pace demonstrated by 81 ARIA versions in 23 days with extensive breaks:

| Phase | Estimate |
|-------|----------|
| Phase 1 | 2-3 days coding, 1 week testing |
| Phase 2 | 3-5 days |
| Phase 3 | 4-6 days |
| Phase 4 | Ongoing |
| **Playable alpha** | **~2 weeks** |
| **Polished experience** | **~4 weeks** |

---

## Risk Assessment

### High Risk: RealTime Rebalance
Nobody plays PZ at 24h days. The interaction between hunger, nutrition, weight, exercise, moodles, and skill gain is complex. Some systems may not scale linearly. Budget extra testing time. This is the make-or-break module — if it doesn't feel right, nothing else matters.

**Mitigation:** Start with minimal changes (just sandbox settings) and only add Lua hooks where testing reveals problems. The game may handle more than expected natively since stats are game-time-based.

### Medium Risk: File Bridge Latency on Remote Server
The bridge architecture depends on where files are written. Client-side bridge (Approach C) is the safest path but means each player needs the companion daemon accessible from their machine.

**Mitigation:** Start with client-side bridge. Both players connect to beardos. If latency is unacceptable, explore Java mod for direct HTTP.

### Medium Risk: Vehicle Interior Mod Compatibility
Project RV Interior is actively maintained but B42 is still in active development. Game updates can break mods. The interior cell system depends on specific map coordinates not conflicting with other mods.

**Mitigation:** Pin the game to a known-stable B42 build. Don't auto-update. Test mod combinations before committing to a long-running world.

### Low Risk: Custom UI
PZ's UI framework is well-documented and proven by multiple complex mods (OmiChat, TICS). Building a chat panel + systems dashboard is standard work.

### Low Risk: AI Personality Quality
Claude Opus 4.6 is more than capable of maintaining distinct personalities with game-state-aware commentary. The iteration is in prompt tuning, not technical feasibility.

---

## File Structure

```
rt-zomboid/
├── fullplan.md                          # This document
├── mod/
│   ├── RTZomboid/
│   │   ├── 42/
│   │   │   ├── media/
│   │   │   │   ├── lua/
│   │   │   │   │   ├── client/
│   │   │   │   │   │   ├── ISUI/
│   │   │   │   │   │   │   ├── BusTerminalUI.lua
│   │   │   │   │   │   │   ├── WalkieUI.lua
│   │   │   │   │   │   │   └── MapAnnotationUI.lua
│   │   │   │   │   │   ├── RTZomboid_ClientBridge.lua
│   │   │   │   │   │   ├── RTZomboid_ContextMenu.lua
│   │   │   │   │   │   └── RTZomboid_MapMarkers.lua
│   │   │   │   │   ├── server/
│   │   │   │   │   │   ├── RTZomboid_AutoSurvival.lua
│   │   │   │   │   │   ├── RTZomboid_ExplorationTracker.lua
│   │   │   │   │   │   ├── RTZomboid_ServerBridge.lua
│   │   │   │   │   │   └── RTZomboid_SkillBooks.lua
│   │   │   │   │   └── shared/
│   │   │   │   │       ├── RTZomboid_Constants.lua
│   │   │   │   │       ├── RTZomboid_Utils.lua
│   │   │   │   │       └── RTZomboid_RealTimeRebalance.lua
│   │   │   │   ├── scripts/
│   │   │   │   │   ├── rt_zomboid_items.txt
│   │   │   │   │   ├── rt_zomboid_recipes.txt
│   │   │   │   │   └── rt_zomboid_vehicles.txt
│   │   │   │   └── textures/
│   │   │   │       └── (custom icons for map markers, UI elements)
│   │   │   └── mod.info
│   │   └── common/                      # Required empty folder for B42
│   └── sandbox-options.txt              # Custom sandbox options for RealTime Rebalance
├── daemon/
│   ├── companion_daemon.py              # Main daemon process
│   ├── krang.py                         # Krang personality + session management
│   ├── eris.py                          # Eris personality + relationship tracking
│   ├── bridge.py                        # File bridge polling + HTTP forwarding
│   ├── game_context.py                  # Game state parsing + context formatting
│   ├── memory_store.py                  # SQLite conversation + event + annotation storage
│   ├── config.py                        # Configuration (AI backend URL, bridge paths, etc.)
│   └── requirements.txt
├── tools/
│   ├── test_bridge.py                   # Bridge communication test
│   ├── test_personalities.py            # AI personality response test
│   └── sandbox_calculator.py            # Helper for calculating rebalance values
└── docs/
    ├── setup_guide.md                   # Server setup + mod installation
    ├── sandbox_settings.md              # Full sandbox configuration reference
    └── personality_tuning.md            # Guide for adjusting Krang/Eris prompts
```

---

## What This Creates

A persistent, real-time zombie survival world where:

1. **Your real day IS your PZ day.** Wake up, check the bus computer, Krang gives you a morning briefing. Go on a supply run before work. Tab away, your character is safe in the bus, auto-managed by Krang. Come home, check the evening report, maybe do a sunset supply run. Your girlfriend joins for an evening session, Eris welcomes her back with commentary about the day.

2. **You're never alone.** Krang and Eris are always there. One keeps you alive, the other keeps you sane. They bicker with each other, remember your past adventures, react to your gameplay. The loneliest game ever made becomes a shared experience with two AI companions who genuinely feel present.

3. **The world is dangerous and persistent.** Tough zombies, constant respawning, helicopter events every week. The bus is your sanctuary. Leaving it is always a calculated risk. Coming back to it always feels like coming home.

4. **The bus is a portal.** From inside the game, you can access your real life — Claude Code, ARIA, email, calendar. Work on real projects from the virtual computer. The boundary between game and reality blurs in the best way.

5. **Your girlfriend gets the full experience.** Not a subset, not a companion app. The same bus, the same AIs, the same world. Eris has a separate relationship with her. Krang tracks both players independently. The annotated map shows both players' exploration.

The Apocalypse Bus plans become real — just virtual.
