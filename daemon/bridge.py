"""File bridge — polls for Lua request files, writes response files.

The PZ client writes JSON request files to ~/Zomboid/Lua/RTZomboid_Bridge/.
This module polls that directory, dispatches requests for processing, and
writes response JSON files back for Lua to pick up.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Awaitable

import config

log = logging.getLogger("rtz")


class FileBridge:
    def __init__(self, bridge_dir: Path,
                 poll_interval: float = 0.5,
                 response_ttl: int = 300):
        self.bridge_dir = bridge_dir
        self.poll_interval = poll_interval
        self.response_ttl = response_ttl
        self._processed_ids: set[str] = set()
        self._running = False
        self._process_fn: Callable[[dict], Awaitable[dict]] | None = None

    def set_processor(self, fn: Callable[[dict], Awaitable[dict]]):
        """Set the async function that processes requests."""
        self._process_fn = fn

    def startup_cleanup(self):
        """Delete stale files from previous runs."""
        if not self.bridge_dir.exists():
            self.bridge_dir.mkdir(parents=True, exist_ok=True)
            log.info("Created bridge directory: %s", self.bridge_dir)
            return

        cleaned = 0
        for f in self.bridge_dir.glob("rt_req_*.json"):
            f.unlink()
            cleaned += 1
        for f in self.bridge_dir.glob("rt_resp_*.json"):
            f.unlink()
            cleaned += 1
        for f in self.bridge_dir.glob("*.tmp"):
            f.unlink()
            cleaned += 1
        if cleaned:
            log.info("Startup cleanup: removed %d stale files", cleaned)

    async def poll_loop(self):
        """Main polling loop."""
        self._running = True
        log.info("Bridge polling started (dir=%s, interval=%.1fs)",
                 self.bridge_dir, self.poll_interval)

        while self._running:
            try:
                await self._poll_once()
            except Exception:
                log.exception("Bridge poll error")
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        self._running = False

    async def _poll_once(self):
        """Scan for request files and process each one."""
        if not self._process_fn:
            return

        # Sort by name for FIFO ordering (timestamp is in the filename)
        req_files = sorted(self.bridge_dir.glob("rt_req_*.json"))

        for req_file in req_files:
            req_id = req_file.stem
            if req_id in self._processed_ids:
                continue

            try:
                raw = req_file.read_text()
                request = json.loads(raw)
            except json.JSONDecodeError:
                log.error("Malformed request file: %s", req_file.name)
                req_file.unlink(missing_ok=True)
                continue
            except OSError as e:
                log.error("Failed to read %s: %s", req_file.name, e)
                continue

            log.info("Processing request: %s (type=%s, personality=%s)",
                     request.get("id", "?"),
                     request.get("type", "?"),
                     request.get("personality", "?"))

            try:
                response = await self._process_fn(request)
                self._write_response(request["id"], response)
                self._processed_ids.add(req_id)
                req_file.unlink(missing_ok=True)
                log.info("Response written for: %s", request["id"])
            except Exception:
                log.exception("Error processing request %s", req_file.name)
                # Don't delete — let it retry on next poll.
                # But add to processed to avoid infinite retry loop.
                self._processed_ids.add(req_id)

    def _write_response(self, request_id: str, response: dict):
        """Write response JSON file atomically (write .tmp, then rename)."""
        resp_file = self.bridge_dir / f"rt_resp_{request_id}.json"
        tmp_file = resp_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(response, ensure_ascii=False))
        tmp_file.rename(resp_file)

    async def write_push_message(self, messages: list[dict]):
        """Write an ambient/push message for Lua to pick up.

        Uses rt_push.json — a single file that Lua polls for.
        Deletes after 2 seconds. Lua debounces reads at 3 seconds,
        so each file is read exactly once.
        """
        push_file = self.bridge_dir / "rt_push.json"
        content = json.dumps({"messages": messages}, ensure_ascii=False)
        tmp = push_file.with_suffix(".tmp")
        tmp.write_text(content)
        tmp.rename(push_file)
        log.info("Push message written (%d messages)", len(messages))
        await asyncio.sleep(2)
        push_file.unlink(missing_ok=True)

    def cleanup_stale_responses(self):
        """Delete response files older than response_ttl seconds."""
        now = time.time()
        for resp_file in self.bridge_dir.glob("rt_resp_*.json"):
            try:
                age = now - resp_file.stat().st_mtime
                if age > self.response_ttl:
                    resp_file.unlink(missing_ok=True)
                    log.debug("Cleaned stale response: %s (age=%.0fs)",
                              resp_file.name, age)
            except OSError:
                pass

        # Clean stale push files too
        push_file = self.bridge_dir / "rt_push.json"
        try:
            if push_file.exists() and now - push_file.stat().st_mtime > 30:
                push_file.unlink(missing_ok=True)
        except OSError:
            pass

        # Also prune processed_ids to prevent unbounded growth
        if len(self._processed_ids) > 1000:
            self._processed_ids.clear()
