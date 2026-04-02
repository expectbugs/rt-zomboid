#!/usr/bin/env python3
"""End-to-end bridge test — simulates what PZ Lua does.

Writes a mock request file to the bridge directory, then polls for the
response file. Run the companion daemon first, then run this script.

Usage:
    # Terminal 1: start the daemon
    cd ~/rt-zomboid && ./venv/bin/python daemon/companion_daemon.py

    # Terminal 2: run the test
    cd ~/rt-zomboid && ./venv/bin/python tools/test_bridge.py
"""

import json
import sys
import time
from pathlib import Path

# Default bridge directory
BRIDGE_DIR = Path("~/Zomboid/Lua/RTZomboid_Bridge").expanduser()


def write_mock_request(bridge_dir: Path, personality: str = "krang",
                       message: str = "System boot. Report status.") -> str:
    """Write a request file mimicking what PZ Lua would write."""
    timestamp_ms = int(time.time() * 1000)
    request_id = f"rt_req_{timestamp_ms}_testplayer"

    request = {
        "id": request_id,
        "timestamp": timestamp_ms,
        "type": "chat",
        "personality": personality,
        "player": "testplayer",
        "message": message,
        "game_state": {
            "game_time": {
                "hour": 14,
                "minute": 30,
                "day": 15,
                "month": 7,
                "world_age_hours": 350.5,
                "days_survived": 14,
            },
            "timestamp_ms": timestamp_ms,
            "player": {
                "hunger": 0.3,
                "thirst": 0.2,
                "fatigue": 0.4,
                "stress": 0.1,
                "boredom": 0.2,
                "pain": 0.0,
                "panic": 0.0,
                "health": 85,
                "position": {"x": 10543, "y": 9876, "z": 0},
                "indoors": True,
            },
            "weather": {
                "temperature": 28,
                "raining": False,
            },
        },
    }

    req_file = bridge_dir / f"{request_id}.json"
    req_file.write_text(json.dumps(request))
    print(f"[TEST] Wrote request: {req_file.name}")
    print(f"[TEST] Message: {message}")
    print(f"[TEST] Personality: {personality}")
    return request_id


def wait_for_response(bridge_dir: Path, request_id: str,
                      timeout: int = 60) -> dict | None:
    """Poll for response file, return decoded JSON or None on timeout."""
    resp_file = bridge_dir / f"rt_resp_{request_id}.json"
    print(f"[TEST] Waiting for response: {resp_file.name} (timeout={timeout}s)")

    start = time.time()
    while time.time() - start < timeout:
        if resp_file.exists():
            try:
                response = json.loads(resp_file.read_text())
                resp_file.unlink()
                return response
            except (json.JSONDecodeError, OSError) as e:
                print(f"[TEST] Error reading response: {e}")
                return None
        time.sleep(0.5)

    return None


def main():
    # Parse args
    personality = "krang"
    message = "System boot. Report status."

    if len(sys.argv) > 1:
        personality = sys.argv[1]
    if len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])

    # Ensure bridge directory exists
    if not BRIDGE_DIR.exists():
        print(f"[TEST] Bridge directory does not exist: {BRIDGE_DIR}")
        print("[TEST] Start the daemon first, or create it manually.")
        sys.exit(1)

    print(f"[TEST] Bridge directory: {BRIDGE_DIR}")
    print()

    # Write request
    request_id = write_mock_request(BRIDGE_DIR, personality, message)

    # Wait for response
    print()
    response = wait_for_response(BRIDGE_DIR, request_id)

    if response is None:
        print("[TEST] TIMEOUT — no response received.")
        print("[TEST] Is the companion daemon running?")
        sys.exit(1)

    # Print response
    print()
    print("=" * 60)
    for msg in response.get("messages", []):
        name = msg.get("personality", "???").upper()
        text = msg.get("text", "(empty)")
        print(f"[{name}]: {text}")
    print("=" * 60)

    if response.get("map_annotations"):
        print(f"\nMap annotations: {response['map_annotations']}")
    if response.get("auto_actions"):
        print(f"Auto actions: {response['auto_actions']}")

    print("\n[TEST] Success!")


if __name__ == "__main__":
    main()
