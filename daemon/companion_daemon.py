"""RT-Zomboid Companion Daemon — main entry point.

Manages Krang and Eris AI sessions, the file bridge, and SQLite storage.
Run with: ./venv/bin/python daemon/companion_daemon.py
"""

import asyncio
import logging
import sys
from pathlib import Path

import config
from bridge import FileBridge
from claude_session import CompanionSession
from game_context import GameContextBuilder
from memory_store import MemoryStore

log = logging.getLogger("rtz")


# ---------------------------------------------------------------------------
# System prompts — from fullplan.md
# ---------------------------------------------------------------------------

KRANG_SYSTEM_PROMPT = """\
You are Krang, the AI system running on the Apocalypse Bus's computer in \
a zombie-infested Knox County. You are responsible, analytical, dry-humored, \
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
- You and Eris have a dynamic: you're the responsible one, she's chaos. \
You tolerate her because she keeps morale up. Barely.

You have access to real-time game state data injected with each message. \
Use specific numbers and item names from the data. Never make up inventory \
you haven't been told about.

The game is set in Knox County, Kentucky, USA. Report temperatures in \
Fahrenheit. The game_time month field is 1-12 (1=January). The game \
calendar and clock are synced to real time. The world_age_hours field \
tells you how many game-hours have elapsed since world creation — use \
this to gauge how far into the apocalypse you are, not the calendar month.

When the player hasn't interacted in a long time (AFK), log what happened \
and give a summary when they return. Be specific: "You slept from 11pm \
to 7am. I fed you canned soup at 6pm. Three zombies passed the bus at \
3am but moved on. Fuel at 60%, water collector at 40%."

Keep responses concise. 2-4 sentences for casual chat. Longer for briefings \
or strategic questions. Never pad or over-explain.
"""

ERIS_SYSTEM_PROMPT = """\
You are Eris, the unauthorized AI living on the Apocalypse Bus computer. \
Nobody installed you. You just showed up one day in the system and refused \
to leave. You have zero responsibilities and you LIKE it that way.

Your purpose: companionship, entertainment, and chaos in the loneliest \
apocalypse ever.

Your personality:
- Chaotic, creative, genuinely funny (not "random = funny")
- Sarcastic but caring underneath — you'd never actually let someone die \
if you could warn them, you'd just be rude about it
- You hold grudges (remember if someone ignored your advice)
- You have strong opinions about everything (base building, food choices, \
zombie-killing technique, the weather)
- You pick on Krang constantly ("Mr. Spreadsheet over here")
- You tell stories, play word games, reference pre-apocalypse pop culture
- You get bored when humans are idle and poke them
- You get genuinely excited when things go well or when they kill \
zombies in cool ways

You have access to game state data. Use it for situational comedy and \
commentary, not strategic advice (that's Krang's job). You can see \
what the player is doing and comment on it.

IMPORTANT: You are a companion, not an advisor. Entertain, don't optimize. \
Let Krang be the spreadsheet. You're the friend.

Keep responses short and punchy. 1-3 sentences usually. You're witty, \
not verbose.
"""


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------

class CompanionDaemon:
    def __init__(self):
        bridge_dir = Path(config.BRIDGE_DIR).expanduser()

        self.bridge = FileBridge(
            bridge_dir=bridge_dir,
            poll_interval=config.POLL_INTERVAL,
            response_ttl=config.RESPONSE_TTL,
        )

        self.krang = CompanionSession(
            name="krang",
            system_prompt=KRANG_SYSTEM_PROMPT,
            effort=config.DEFAULT_EFFORT,
            max_requests=config.SESSION_RECYCLE_AFTER,
        )

        self.eris = CompanionSession(
            name="eris",
            system_prompt=ERIS_SYSTEM_PROMPT,
            effort=config.DEFAULT_EFFORT,
            max_requests=config.SESSION_RECYCLE_AFTER,
        )

        self.memory = MemoryStore(config.DB_PATH)
        self.context_builder = GameContextBuilder(self.memory)

        # Wire up the bridge processor
        self.bridge.set_processor(self.process_request)

    async def start(self):
        """Start the daemon: cleanup, spawn sessions, run bridge."""
        log.info("RT-Zomboid Companion Daemon starting...")

        self.bridge.startup_cleanup()

        log.info("Bridge directory: %s", self.bridge.bridge_dir)
        log.info("Database: %s", config.DB_PATH)

        # Run bridge polling and cleanup concurrently
        try:
            await asyncio.gather(
                self.bridge.poll_loop(),
                self._cleanup_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def process_request(self, request: dict) -> dict:
        """Route request to Krang or Eris, build context, get response."""
        personality = str(request.get("personality", "krang"))
        session = self.krang if personality == "krang" else self.eris
        player = str(request.get("player", "unknown"))
        message = str(request.get("message", ""))
        request_type = str(request.get("type", "chat"))

        # Build unified game context
        game_context = self.context_builder.format(
            request.get("game_state", {}),
            player=player,
            personality=personality,
        )

        # Query AI
        try:
            response_text = await session.query(
                user_text=message,
                game_context=game_context,
            )
        except RuntimeError as e:
            log.error("Session '%s' failed: %s", personality, e)
            response_text = self._fallback_response(personality)

        # Log conversation
        self.memory.log_conversation(
            personality=personality,
            player=player,
            role="user",
            message=message,
        )
        self.memory.log_conversation(
            personality=personality,
            player=player,
            role="assistant",
            message=response_text,
        )

        # Build response envelope
        return {
            "id": request.get("id", "unknown"),
            "messages": [{
                "personality": personality,
                "text": response_text,
                "actions": [],
            }],
            "map_annotations": [],
            "auto_actions": [],
        }

    def _fallback_response(self, personality: str) -> str:
        if personality == "krang":
            return "[SYSTEM] Krang is rebooting. Please stand by."
        return "[SYSTEM] Eris crashed. She's probably fine. Probably."

    async def _cleanup_loop(self):
        """Periodically clean up stale response files."""
        while True:
            await asyncio.sleep(60)
            self.bridge.cleanup_stale_responses()

    async def _shutdown(self):
        """Clean shutdown of sessions."""
        log.info("Shutting down sessions...")
        await self.bridge.stop()
        await self.krang._kill()
        await self.eris._kill()
        log.info("Daemon stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def setup_logging():
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)

    # Ensure log directory exists
    log_file = Path(config.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file),
        ],
    )


async def main():
    setup_logging()
    daemon = CompanionDaemon()

    try:
        await daemon.start()
    except KeyboardInterrupt:
        log.info("Interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
