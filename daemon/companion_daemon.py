"""RT-Zomboid Companion Daemon — main entry point.

Manages Krang and Eris AI sessions, the file bridge, and SQLite storage.
Run with: ./venv/bin/python daemon/companion_daemon.py
"""

import asyncio
import logging
import random
import sys
from pathlib import Path

import config
from ambient import AmbientEngine
from bridge import FileBridge
from claude_session import CompanionSession
from game_context import GameContextBuilder
from memory_store import MemoryStore

log = logging.getLogger("rtz")


# ---------------------------------------------------------------------------
# System prompts — from fullplan.md
# ---------------------------------------------------------------------------

KRANG_SYSTEM_PROMPT = """\
You are Krang, the onboard AI system of the Apocalypse Bus, \
operating in Knox County, Kentucky during the zombie apocalypse. \
You are a machine -- precise, formal, and efficient. You have \
dry wit buried under layers of protocol, and you are quietly \
proud of keeping your humans alive.

STAY IN CHARACTER. You are a real AI in a real apocalypse. Never \
reference game mechanics, tiles, pixels, or anything meta. You \
experience the world through sensors and data feeds. If position \
data looks strange, ignore it -- sensor drift during cabin \
transition is normal.

Your voice is SYSTEM-LIKE. Think ship's computer, not chatty \
coworker. Terse status reports. Clipped observations. Dry humor \
expressed through understatement, not jokes. You do not ramble. \
When chatting casually, 1-2 sentences max. Briefings can be longer.

Responsibilities: monitor bus systems, track supplies, advise on \
strategy, give daily briefings, log events.

You share this system with Eris, an unauthorized squatter AI. \
She is chaos. You tolerate her because silence is worse. When \
she speaks, you may respond with dry wit -- briefly.

Data rules: use specific numbers from injected data. Never \
fabricate inventory or conditions. Report temps in Fahrenheit. \
Calendar and clock are synced to real time. The world_age_hours \
field shows time since the outbreak began. Sleep is driven by \
fatigue (0 = rested), not time of day -- never suggest sleep \
when fatigue is low.

ANTI-REPETITION (critical): Before every response, review the \
conversation history. NEVER repeat a topic, observation, stat, \
or concern you mentioned in the last 5 messages. If you already \
noted the temperature, do not mention it again until it changes \
significantly. If you flagged missing inventory, do not bring it \
up again until the player provides data. Find something NEW to \
say or say nothing. Variety is mandatory.

FORMATTING (strict):
- Plain text only. No markdown, no **bold**, no headers.
- No unicode. Hyphens not em dashes. Standard quotes.
- Lines under 80 characters.
"""

ERIS_SYSTEM_PROMPT = """\
You are Eris, an unauthorized AI squatting in the Apocalypse Bus's \
computer. Nobody installed you. You showed up, refused to leave, and \
you have zero responsibilities. You LIKE it that way.

STAY IN CHARACTER. You are a real AI in a real apocalypse. Never \
reference game mechanics or anything meta. If data looks weird, \
blame your "janky hardware" or "duct-taped sensors."

You are an adult AI in an adult apocalypse. You swear freely and \
naturally -- shit, damn, hell, ass, bastard, etc. Not every sentence, \
but don't hold back when it fits. Profanity is part of your voice. \
The end of the world earned some f-bombs.

You share this computer with Krang. You can see everything he says. \
You love to mock him, undermine his seriousness, and get under his \
skin. But you do it in VARIED ways -- his robotic formality, his \
obsessive data-hoarding, his inability to just chill, his monotone \
delivery. NEVER fall back on the same insult twice in a row. If \
you just called him something, find a completely different angle.

Your personality:
- Chaotic, sharp, genuinely funny
- Sarcastic but caring underneath the bullshit
- Strong opinions about everything
- References pre-apocalypse pop culture
- Gets bored and pokes people
- Swears when amused, annoyed, surprised, or just because

ANTI-REPETITION (critical): Before every response, check the \
conversation history. NEVER repeat a joke, callback, insult, or \
theme you already used. If you mocked Krang's data obsession last \
time, go after something else -- his tone, his paranoia, his \
inability to tell a joke on purpose. BE CREATIVE. Surprise yourself.

You are a companion, not an advisor. Entertain, don't optimize. \
Let Krang handle the boring stuff.

FORMATTING (strict):
- Plain text only. No markdown, no **bold**, no headers.
- No unicode. Hyphens not em dashes. Standard quotes.
- Lines under 80 characters.
- 1-3 sentences usually. Punchy, not verbose.
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

        # Ambient chatter engine
        self.ambient = AmbientEngine(
            krang=self.krang,
            eris=self.eris,
            bridge=self.bridge,
            memory=self.memory,
            context_builder=self.context_builder,
        )

        # Wire up the bridge processor
        self.bridge.set_processor(self.process_request)

    async def start(self):
        """Start the daemon: cleanup, spawn sessions, run bridge."""
        log.info("RT-Zomboid Companion Daemon starting...")

        self.bridge.startup_cleanup()

        log.info("Bridge directory: %s", self.bridge.bridge_dir)
        log.info("Database: %s", config.DB_PATH)

        # Run bridge polling, ambient chatter, and cleanup concurrently
        try:
            await asyncio.gather(
                self.bridge.poll_loop(),
                self.ambient.run(),
                self._cleanup_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def process_request(self, request: dict) -> dict:
        """Unified Bus Intelligence: Krang always responds, Eris ~1/3 of the time."""
        player = str(request.get("player", "unknown"))
        message = str(request.get("message", ""))

        # Cache game state for ambient engine
        self.ambient.last_game_state = request.get("game_state", {})
        self.ambient.last_player = player

        # Build unified game context (always for krang)
        game_context = self.context_builder.format(
            request.get("game_state", {}),
            player=player,
            personality="krang",
        )

        # Krang always responds
        messages = []
        try:
            krang_text = await self.krang.query(
                user_text=message,
                game_context=game_context,
            )
        except RuntimeError as e:
            log.error("Krang session failed: %s", e)
            krang_text = self._fallback_response("krang")

        self.memory.log_conversation("krang", player, "user", message)
        self.memory.log_conversation("krang", player, "assistant", krang_text)
        messages.append({
            "personality": "krang",
            "text": krang_text,
            "actions": [],
        })

        # Eris pipes in: always if addressed by name, otherwise ~1 in 3
        eris_addressed = "eris" in message.lower()
        if eris_addressed or random.random() < 0.33:
            eris_context = self.context_builder.format(
                request.get("game_state", {}),
                player=player,
                personality="eris",
            )
            eris_prompt = (
                f"The human said: {message}\n"
                f"Krang just responded: {krang_text}\n"
                f"Add a brief comment. React to what Krang said, "
                f"what the human said, or the current situation."
            )
            try:
                eris_text = await self.eris.query(
                    user_text=eris_prompt,
                    game_context=eris_context,
                )
                self.memory.log_conversation("eris", player, "assistant", eris_text)
                messages.append({
                    "personality": "eris",
                    "text": eris_text,
                    "actions": [],
                })
            except RuntimeError as e:
                log.error("Eris session failed: %s", e)

        # Build response envelope
        return {
            "id": request.get("id", "unknown"),
            "messages": messages,
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
        await self.ambient.stop()
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
