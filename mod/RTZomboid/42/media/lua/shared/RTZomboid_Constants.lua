-- RT-Zomboid shared constants
-- Used by both client and server Lua code

RTZ = RTZ or {}

RTZ.MOD_ID = "RTZomboid"
RTZ.VERSION = "0.2.0"

-- File bridge settings
RTZ.BRIDGE_PREFIX = "RTZomboid_Bridge/"
RTZ.REQ_PREFIX = "rt_req_"
RTZ.RESP_PREFIX = "rt_resp_"

-- Polling: check for responses every 30 ticks (~500ms at 60fps)
RTZ.POLL_INTERVAL_TICKS = 30

-- Request timeout: consider a request failed after 60 seconds
RTZ.REQUEST_TIMEOUT_MS = 60000

-- Max simultaneous pending requests
RTZ.MAX_PENDING = 10

-- AI personalities
RTZ.PERSONALITIES = {
    KRANG = "krang",
    ERIS = "eris",
}

-- Request types
RTZ.REQUEST_TYPES = {
    CHAT = "chat",
    STATUS = "status",
    SYSTEM = "system",
    MAP_UPDATE = "map_update",
}
