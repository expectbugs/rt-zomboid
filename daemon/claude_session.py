"""Persistent Claude CLI session manager for RT-Zomboid companions.

Adapted from ARIA's ClaudeSession (~/aria/claude_session.py). Manages a
persistent Claude CLI subprocess using the stream-json protocol. Each
companion personality (Krang, Eris) gets its own session with a dedicated
system prompt.
"""

import asyncio
import json
import logging
import os

import config

log = logging.getLogger("rtz")


class CompanionSession:
    """Manages a persistent Claude CLI subprocess for one AI personality."""

    def __init__(self, name: str, system_prompt: str, effort: str = "auto",
                 max_requests: int = 150):
        self.name = name
        self._system_prompt = system_prompt
        self._effort = effort
        self._max_requests = max_requests
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._request_count = 0
        self._context_bytes = 0
        self._max_context_bytes = 500_000  # ~125K tokens

    def _is_alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def _spawn(self):
        """Spawn a fresh Claude CLI process with stream-json I/O."""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["CLAUDE_CODE_EFFORT_LEVEL"] = self._effort
        env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"

        self._proc = await asyncio.create_subprocess_exec(
            config.CLAUDE_CLI,
            "--print",
            "--output-format", "stream-json",
            "--input-format", "stream-json",
            "--verbose",
            "--model", "opus",
            "--dangerously-skip-permissions",
            "--system-prompt", self._system_prompt,
            "--settings", '{"claudeMdExcludes": ["/home/user/rt-zomboid/CLAUDE.md"]}',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            limit=16 * 1024 * 1024,  # 16MB readline buffer
        )
        self._request_count = 0
        self._context_bytes = 0
        log.info("Session '%s' spawned (pid=%s, effort=%s)",
                 self.name, self._proc.pid, self._effort)

    async def _kill(self):
        """Kill the current process if alive."""
        if self._is_alive():
            try:
                self._proc.kill()
                await self._proc.wait()
            except Exception:
                pass
        self._proc = None

    async def _ensure_alive(self):
        """Ensure the subprocess is running. Respawn if dead or stale."""
        if not self._is_alive() or self._request_count >= self._max_requests:
            if self._is_alive():
                log.info("Recycling session '%s' after %d requests",
                         self.name, self._request_count)
                await self._kill()
            await self._spawn()

    async def query(self, user_text: str, game_context: str = "") -> str:
        """Send a prompt to the persistent Claude process and return the response."""
        async with self._lock:
            await self._ensure_alive()

            # Build prompt with context
            parts = []
            if game_context:
                parts.append(f"[CONTEXT]\n{game_context}\n[/CONTEXT]")
            parts.append(user_text)
            prompt = "\n".join(parts)

            # Track context size
            self._context_bytes += len(prompt)

            # Send user message as NDJSON
            msg = json.dumps({
                "type": "user",
                "message": {"role": "user", "content": prompt},
            }) + "\n"
            self._proc.stdin.write(msg.encode())
            await self._proc.stdin.drain()
            self._request_count += 1

            # Read stdout lines until we get a result.
            # Collect all assistant text blocks — the "result" message only
            # contains the LAST text block (learned from ARIA session_pool.py).
            assistant_text_parts: list[str] = []
            try:
                while True:
                    line = await asyncio.wait_for(
                        self._proc.stdout.readline(),
                        timeout=config.CLAUDE_TIMEOUT,
                    )
                    if not line:
                        raise RuntimeError(
                            f"Session '{self.name}' exited unexpectedly")

                    try:
                        data = json.loads(line.decode().strip())
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type")

                    if msg_type == "result":
                        if data.get("is_error"):
                            raise RuntimeError(
                                f"Session '{self.name}' error: "
                                f"{data.get('result', 'unknown')}")

                        result_text = data.get("result", "")

                        # Prepend earlier assistant text blocks not in the result
                        if len(assistant_text_parts) > 1:
                            earlier = [
                                p.strip() for p in assistant_text_parts
                                if p.strip() and p.strip() not in result_text
                            ]
                            if earlier:
                                result_text = "\n".join(earlier) + "\n" + result_text

                        # Check context pressure
                        self._context_bytes += len(result_text)
                        if self._context_bytes > self._max_context_bytes:
                            log.info(
                                "Session '%s' at %d bytes, scheduling recycle",
                                self.name, self._context_bytes)
                            self._request_count = self._max_requests

                        return result_text

                    elif msg_type == "assistant":
                        # Collect text blocks from assistant messages
                        msg_data = data.get("message", {})
                        if isinstance(msg_data, dict):
                            content = msg_data.get("content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if (isinstance(block, dict)
                                            and block.get("type") == "text"):
                                        text_val = block.get("text", "")
                                        if text_val.strip():
                                            assistant_text_parts.append(text_val)

                    elif msg_type == "control_request":
                        # Auto-approve any permission/hook requests
                        resp = json.dumps({
                            "type": "control_response",
                            "response": {
                                "subtype": "success",
                                "request_id": data.get("request_id"),
                                "response": {"behavior": "allow"},
                            }
                        }) + "\n"
                        self._proc.stdin.write(resp.encode())
                        await self._proc.stdin.drain()

                    # Ignore other types (system, stream_event, etc.)

            except asyncio.TimeoutError:
                log.error("Session '%s' timed out after %ss",
                          self.name, config.CLAUDE_TIMEOUT)
                await self._kill()
                raise RuntimeError(
                    f"Session '{self.name}' timed out after {config.CLAUDE_TIMEOUT}s")
            except Exception:
                log.exception("Session '%s' error, killing process", self.name)
                await self._kill()
                raise
