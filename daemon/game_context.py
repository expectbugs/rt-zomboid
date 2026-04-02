"""Game state context builder for AI companion queries.

Every request to Krang or Eris goes through this module to build a consistent
context string from the raw game state data. Never build context ad-hoc —
all AI requests get the same format. (Lesson from ARIA.)
"""

from datetime import datetime

from memory_store import MemoryStore


class GameContextBuilder:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def format(self, game_state: dict, player: str, personality: str) -> str:
        """Build a complete context string for a Claude query."""
        sections = []

        # Game time
        gt = game_state.get("game_time", {})
        if gt:
            hour = int(gt.get("hour", 0))
            minute = int(gt.get("minute", 0))
            day = int(gt.get("day", 0))
            month = int(gt.get("month", 0))
            days_survived = int(gt.get("days_survived", 0))
            sections.append(
                f"[GAME TIME] Month {month}, Day {day}, "
                f"{hour:02d}:{minute:02d} | Day {days_survived} survived"
            )

        # Real wall clock (from daemon, authoritative)
        sections.append(
            f"[REAL TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Player stats — cast everything defensively
        ps = game_state.get("player", {})
        if ps:
            sections.append(self._format_player_stats(ps, player))

        # Weather
        weather = game_state.get("weather", {})
        if weather:
            parts = []
            if "temperature" in weather:
                temp_c = float(weather["temperature"])
                temp_f = temp_c * 9 / 5 + 32
                parts.append(f"{temp_f:.0f}F")
            if "precipitation" in weather:
                precip = float(weather["precipitation"])
                if precip > 0:
                    parts.append("raining")
                else:
                    parts.append("dry")
            if parts:
                sections.append(f"[WEATHER] {', '.join(parts)}")

        # Recent conversation history
        history = self.memory.get_recent_conversations(
            personality=personality, player=player, limit=5,
        )
        if history:
            sections.append(self._format_history(history))

        # Eris relationship score
        if personality == "eris":
            score = self.memory.get_relationship_score(player)
            sections.append(f"[RELATIONSHIP SCORE] {score}/100 with {player}")

        return "\n".join(sections)

    def _format_player_stats(self, ps: dict, player: str) -> str:
        parts = [f"[PLAYER: {player}]"]

        stat_names = [
            ("hunger", "Hunger"),
            ("thirst", "Thirst"),
            ("fatigue", "Fatigue"),
            ("stress", "Stress"),
            ("boredom", "Boredom"),
            ("pain", "Pain"),
            ("panic", "Panic"),
        ]

        stat_parts = []
        for key, label in stat_names:
            if key in ps:
                val = float(ps[key])
                stat_parts.append(f"{label}: {val:.0%}")

        if "health" in ps:
            stat_parts.append(f"Health: {float(ps['health']):.0f}")

        if stat_parts:
            parts.append(" ".join(stat_parts))

        pos = ps.get("position", {})
        if pos:
            parts.append(
                f"Position: ({int(pos.get('x', 0))}, {int(pos.get('y', 0))})"
            )

        if "indoors" in ps:
            parts.append("Indoors" if ps["indoors"] else "Outdoors")

        return " | ".join(parts)

    def _format_history(self, turns: list[dict]) -> str:
        lines = ["[RECENT CONVERSATION]"]
        for turn in turns:
            role = str(turn["role"]).upper()
            msg = str(turn["message"])
            if len(msg) > 500:
                msg = msg[:500] + "..."
            lines.append(f"  {role}: {msg}")
        lines.append("[/RECENT CONVERSATION]")
        return "\n".join(lines)
