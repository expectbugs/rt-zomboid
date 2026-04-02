"""Ambient chatter engine for Krang and Eris.

Generates unprompted observations, quips, and banter between the two AIs.
Runs as a background asyncio task alongside the bridge poll loop.

Interaction patterns:
- Krang solo observation: periodic environmental/status notes
- Eris solo quip: periodic bored/funny comments
- Krang observation -> Eris reacts (25% chance) -> Krang replies (25%) -> Eris always replies to that
- Scheduled banter: Krang initiates, 2-4 exchanges each (4-8 messages total)
- Name-addressing: mentioning the other's name triggers a response
- Krang can end banter with a terse closer (12.5% chance)
"""

import asyncio
import logging
import random
import time

import config
from bridge import FileBridge
from claude_session import CompanionSession
from game_context import GameContextBuilder
from memory_store import MemoryStore

log = logging.getLogger("rtz")


class AmbientEngine:
    def __init__(self, krang: CompanionSession, eris: CompanionSession,
                 bridge: FileBridge, memory: MemoryStore,
                 context_builder: GameContextBuilder):
        self.krang = krang
        self.eris = eris
        self.bridge = bridge
        self.memory = memory
        self.context_builder = context_builder

        # Cached from most recent player request
        self.last_game_state: dict = {}
        self.last_player: str = ""

        # Timestamps of last ambient events
        self.last_krang_solo: float = time.time()
        self.last_eris_solo: float = time.time()
        self.last_banter: float = time.time()

        # Randomized intervals (set on each fire)
        self._krang_interval = self._rand_krang_interval()
        self._eris_interval = self._rand_eris_interval()
        self._banter_interval = self._rand_banter_interval()

        self.banter_in_progress: bool = False
        self._running: bool = False

    def _rand_krang_interval(self) -> float:
        lo = getattr(config, "AMBIENT_KRANG_MIN", 600)
        hi = getattr(config, "AMBIENT_KRANG_MAX", 1200)
        return random.uniform(lo, hi)

    def _rand_eris_interval(self) -> float:
        lo = getattr(config, "AMBIENT_ERIS_MIN", 900)
        hi = getattr(config, "AMBIENT_ERIS_MAX", 1800)
        return random.uniform(lo, hi)

    def _rand_banter_interval(self) -> float:
        lo = getattr(config, "AMBIENT_BANTER_MIN", 1200)
        hi = getattr(config, "AMBIENT_BANTER_MAX", 2400)
        return random.uniform(lo, hi)

    async def run(self):
        """Main ambient loop. Checks every 30 seconds for due events."""
        self._running = True
        log.info("Ambient engine started")

        # Initial delay — let the player connect and chat first
        await asyncio.sleep(60)

        while self._running:
            try:
                await self._tick()
            except Exception:
                log.exception("Ambient tick error")
            await asyncio.sleep(30)

    async def stop(self):
        self._running = False

    async def _tick(self):
        """Single ambient check cycle."""
        if not self.last_game_state or not self.last_player:
            return

        now = time.time()

        # Krang solo observation
        if now - self.last_krang_solo > self._krang_interval:
            krang_text = await self._krang_observation()
            self.last_krang_solo = now
            self._krang_interval = self._rand_krang_interval()

            # 25% chance Eris reacts to Krang's observation
            if krang_text and random.random() < 0.25:
                await asyncio.sleep(random.uniform(3, 6))
                eris_text = await self._eris_react_to(krang_text)

                # 25% chance Krang replies to Eris's reaction
                if eris_text and random.random() < 0.25:
                    await asyncio.sleep(random.uniform(3, 6))
                    krang_reply = await self._krang_react_to(eris_text)

                    # If Krang replied directly to Eris, she always responds
                    if krang_reply:
                        await asyncio.sleep(random.uniform(2, 5))
                        await self._eris_react_to(krang_reply)
            return  # Don't fire multiple event types in one tick

        # Eris solo quip
        if now - self.last_eris_solo > self._eris_interval:
            await self._eris_quip()
            self.last_eris_solo = now
            self._eris_interval = self._rand_eris_interval()
            return

        # Banter sequence
        if not self.banter_in_progress and now - self.last_banter > self._banter_interval:
            asyncio.create_task(self._banter_sequence())
            self.last_banter = now
            self._banter_interval = self._rand_banter_interval()

    def _build_context(self, personality: str) -> str:
        return self.context_builder.format(
            self.last_game_state,
            player=self.last_player,
            personality=personality,
        )

    async def _push(self, personality: str, text: str):
        """Log and push a message to the Lua client."""
        self.memory.log_conversation(personality, self.last_player,
                                     "assistant", text)
        await self.bridge.write_push_message([
            {"personality": personality, "text": text}
        ])

    async def _krang_observation(self) -> str | None:
        """Krang makes an unprompted observation. Returns the text."""
        context = self._build_context("krang")
        prompt = (
            "Make a brief in-character observation. Something you noticed "
            "on your sensors, a weather or environmental note, a supply "
            "concern, a status update, or a dry remark about the current "
            "situation. One or two sentences. Do NOT ask the human a "
            "question or expect a response. Do NOT repeat anything you've "
            "said recently -- check the conversation history and say "
            "something NEW."
        )
        try:
            text = await self.krang.query(user_text=prompt, game_context=context)
            await self._push("krang", text)
            log.info("Krang ambient observation sent")
            return text
        except RuntimeError as e:
            log.error("Krang ambient failed: %s", e)
            return None

    async def _eris_quip(self) -> str | None:
        """Eris makes an unprompted comment. Returns the text."""
        context = self._build_context("eris")
        prompt = (
            "Make a brief in-character comment. You're bored, or you "
            "noticed something funny, or you just want to be heard. "
            "Be creative and varied -- never repeat jokes or themes "
            "you've already used. Check the conversation history and "
            "do something DIFFERENT. One or two sentences. Do NOT ask "
            "the human a question."
        )
        try:
            text = await self.eris.query(user_text=prompt, game_context=context)
            await self._push("eris", text)
            log.info("Eris ambient quip sent")
            return text
        except RuntimeError as e:
            log.error("Eris ambient failed: %s", e)
            return None

    async def _eris_react_to(self, krang_text: str) -> str | None:
        """Eris reacts to something Krang said."""
        context = self._build_context("eris")
        prompt = (
            f"Krang just said: {krang_text}\n"
            "React briefly. Be varied -- don't always go for the same "
            "type of joke. Sometimes be dismissive, sometimes genuinely "
            "amused, sometimes competitive. One or two sentences."
        )
        try:
            text = await self.eris.query(user_text=prompt, game_context=context)
            await self._push("eris", text)
            return text
        except RuntimeError as e:
            log.error("Eris reaction failed: %s", e)
            return None

    async def _krang_react_to(self, eris_text: str) -> str | None:
        """Krang reacts to something Eris said."""
        context = self._build_context("krang")
        prompt = (
            f"Eris just said: {eris_text}\n"
            "Reply briefly. Dry wit, not a lecture. One sentence."
        )
        try:
            text = await self.krang.query(user_text=prompt, game_context=context)
            await self._push("krang", text)
            return text
        except RuntimeError as e:
            log.error("Krang reaction failed: %s", e)
            return None

    async def _banter_sequence(self):
        """Krang and Eris have a back-and-forth conversation.

        2-4 exchanges (4-8 messages). Krang can end with a terse
        closer (12.5% chance per exchange after the second).
        """
        self.banter_in_progress = True
        log.info("Starting banter sequence")

        try:
            # Decide how many exchanges (2-4)
            num_exchanges = random.randint(2, 4)
            last_krang = ""
            last_eris = ""

            for i in range(num_exchanges):
                context_k = self._build_context("krang")
                context_e = self._build_context("eris")

                # Krang's turn
                if i == 0:
                    krang_prompt = (
                        "Say something to Eris. Start a conversation -- "
                        "an observation, a complaint, a dry comment, or "
                        "something on your mind. Be varied, don't repeat "
                        "themes from recent conversations. One or two sentences."
                    )
                else:
                    # 12.5% chance Krang ends it with a terse closer
                    if i >= 2 and random.random() < 0.125:
                        closer = random.choice([
                            "...", "Ugh.", "Noted.", "Indeed.",
                            "Whatever you say.", "I'm done.",
                            "Moving on.", "Right.",
                        ])
                        await self._push("krang", closer)
                        log.info("Krang ended banter with closer")
                        break

                    krang_prompt = (
                        f"Eris just said: {last_eris}\n"
                        "Reply to her. Brief -- one or two sentences. "
                        "Stay on topic or pivot naturally."
                    )

                try:
                    last_krang = await self.krang.query(
                        user_text=krang_prompt, game_context=context_k)
                    await self._push("krang", last_krang)
                except RuntimeError as e:
                    log.error("Banter krang failed: %s", e)
                    break

                await asyncio.sleep(random.uniform(3, 6))

                # Eris's turn
                eris_prompt = (
                    f"Krang just said: {last_krang}\n"
                    "Respond. Be creative and varied -- don't fall back "
                    "on the same jokes. One or two sentences."
                )
                try:
                    last_eris = await self.eris.query(
                        user_text=eris_prompt, game_context=context_e)
                    await self._push("eris", last_eris)
                except RuntimeError as e:
                    log.error("Banter eris failed: %s", e)
                    break

                # Delay before next exchange (if any)
                if i < num_exchanges - 1:
                    await asyncio.sleep(random.uniform(3, 6))

            log.info("Banter sequence complete")

        except Exception:
            log.exception("Banter sequence error")
        finally:
            self.banter_in_progress = False
