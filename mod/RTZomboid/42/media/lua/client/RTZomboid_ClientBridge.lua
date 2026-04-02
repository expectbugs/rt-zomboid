-- RT-Zomboid Client Bridge
-- Writes JSON request files for the companion daemon, polls for responses.
-- All file I/O targets ~/Zomboid/Lua/RTZomboid_Bridge/ (created by daemon).

-- RTZomboid_Constants.lua and RTZomboid_JSON.lua are auto-loaded from shared/
-- before client files. Globals RTZ and RTZ_JSON are already available.

RTZ_Bridge = {}

-- Internal state
RTZ_Bridge._pending = {}       -- {id = {id=str, sent_ms=number, personality=str}}
RTZ_Bridge._tick_count = 0
RTZ_Bridge._initialized = false
RTZ_Bridge._processed = {}     -- {response_filename = true} to avoid re-reading


-- Initialize the bridge on game start
function RTZ_Bridge.init()
    RTZ_Bridge._pending = {}
    RTZ_Bridge._tick_count = 0
    RTZ_Bridge._processed = {}
    RTZ_Bridge._last_push_read = 0
    RTZ_Bridge._initialized = true
    print("[RTZ] Client bridge initialized (v" .. RTZ.VERSION .. ")")
end


-- Send a request to the companion daemon via file bridge.
-- Returns the request ID, or nil on failure.
function RTZ_Bridge.sendRequest(requestType, personality, message)
    if not RTZ_Bridge._initialized then
        print("[RTZ] ERROR: Bridge not initialized")
        return nil
    end

    -- Enforce pending request limit
    local pendingCount = 0
    for _ in pairs(RTZ_Bridge._pending) do
        pendingCount = pendingCount + 1
    end
    if pendingCount >= RTZ.MAX_PENDING then
        print("[RTZ] WARNING: Too many pending requests (" .. pendingCount .. "), dropping")
        return nil
    end

    local player = getPlayer()
    if not player then
        print("[RTZ] ERROR: No player available")
        return nil
    end

    -- getTimestampMs() returns a Lua number (vanilla: ISButton.lua:279)
    -- player:getUsername() returns a Lua string (vanilla: ISChat.lua)
    local timestampMs = getTimestampMs()
    local playerName = player:getUsername()
    local requestId = RTZ.REQ_PREFIX .. tostring(timestampMs) .. "_" .. playerName

    -- Collect game state using only verified vanilla APIs
    local gameState = RTZ_Bridge.collectGameState(player)

    -- Build the request table — all values are Lua primitives at this point
    local request = {
        id = requestId,
        timestamp = timestampMs,
        type = requestType,
        personality = personality,
        player = playerName,
        message = message,
        game_state = gameState,
    }

    -- Encode to JSON
    local ok, jsonStr = pcall(RTZ_JSON.encode, request)
    if not ok then
        -- Extract actual error message from Java RuntimeException wrapper
        local errMsg = tostring(jsonStr)
        print("[RTZ] ERROR encoding request: " .. errMsg)
        -- Debug: dump table structure
        RTZ_Bridge.debugDumpTable(request, "request")
        return nil
    end

    -- Write to bridge directory
    -- getFileWriter(filename, createIfNull, append) — vanilla: ISLayoutManager.lua:178
    local filename = RTZ.BRIDGE_PREFIX .. requestId .. ".json"
    local writeOk, writeErr = pcall(function()
        local writer = getFileWriter(filename, true, false)
        writer:write(jsonStr)
        writer:close()
    end)

    if not writeOk then
        print("[RTZ] ERROR writing request file: " .. tostring(writeErr))
        return nil
    end

    -- Track pending request
    RTZ_Bridge._pending[requestId] = {
        id = requestId,
        sent_ms = timestampMs,
        personality = personality,
    }

    print("[RTZ] Request sent: " .. requestId .. " -> " .. personality)
    return requestId
end


-- Debug helper: dump table keys/types to console
function RTZ_Bridge.debugDumpTable(tbl, prefix)
    if type(tbl) ~= "table" then
        print("[RTZ] DEBUG " .. prefix .. " = (" .. type(tbl) .. ") " .. tostring(tbl))
        return
    end
    for k, v in pairs(tbl) do
        local keyType = type(k)
        local valType = type(v)
        if valType == "table" then
            print("[RTZ] DEBUG " .. prefix .. "." .. tostring(k) .. " [key:" .. keyType .. "] = (table)")
            RTZ_Bridge.debugDumpTable(v, prefix .. "." .. tostring(k))
        else
            print("[RTZ] DEBUG " .. prefix .. "." .. tostring(k) .. " [key:" .. keyType .. "] = (" .. valType .. ") " .. tostring(v))
        end
    end
end


-- Collect current game state for context injection.
-- Uses ONLY APIs verified in vanilla PZ source code.
function RTZ_Bridge.collectGameState(player)
    local state = {}

    -- Game time — all verified in B42 client source:
    --   getHour(): ClimateDebug.lua:234
    --   getDay(): ClimateDebug.lua:242
    --   getMonth(): ClimateDebug.lua:247, ISFarmingMenu.lua:1011
    --   getWorldAgeHours(): ISButtonPrompt.lua:423
    --   NOTE: getNightsSurvived() and getDaysSurvived() NOT in B42 client.
    --         getMinutes() does NOT exist on GameTime.
    -- getMonth() and getDay() are 0-indexed in Kahlua.
    -- Vanilla adds +1 for display: DebugDemoTime.lua:149, ISFarmingMenu.lua:1011
    local gt = getGameTime()
    if gt then
        state.game_time = {
            hour = gt:getHour(),
            day = gt:getDay() + 1,
            month = gt:getMonth() + 1,
            world_age_hours = gt:getWorldAgeHours(),
        }
    end

    -- Wall-clock timestamp — verified: ISButton.lua:279, ISBaseIcon.lua:33
    state.timestamp_ms = getTimestampMs()

    -- Player stats — B42 uses stats:get(CharacterStat.X) pattern
    --   Verified: ISStatsAndBody.lua:127, ISSleepDialog.lua:16,
    --   ISWorldObjectContextMenu.lua:1059, ISAnimalContextMenu.lua:30
    local stats = player:getStats()
    if stats then
        state.player = {
            hunger = stats:get(CharacterStat.HUNGER),
            thirst = stats:get(CharacterStat.THIRST),
            fatigue = stats:get(CharacterStat.FATIGUE),
            endurance = stats:get(CharacterStat.ENDURANCE),
            stress = stats:get(CharacterStat.STRESS),
            boredom = stats:get(CharacterStat.BOREDOM),
            pain = stats:get(CharacterStat.PAIN),
            panic = stats:get(CharacterStat.PANIC),
            unhappiness = stats:get(CharacterStat.UNHAPPINESS),
        }
    end

    -- Body damage — verified in B42 client: ISStatsAndBody.lua:241-244
    --   getOverallBodyHealth(): confirmed
    --   getBodyParts(): ISHealthPanel.lua:509, AReallyCDDAy.lua:80
    --   Iteration: bodyParts:size(), bodyParts:get(i-1) — ISHealthPanel.lua:513-514
    --   BodyPart methods: HasInjury(), bandaged(), scratched(), isDeepWounded(),
    --     getFractureTime(), getSplintFactor(), getType() — ISHealthPanel.lua:516
    --   BodyPartType.ToString(type): ISHealthPanel.lua:278
    local bd = player:getBodyDamage()
    if bd then
        state.player = state.player or {}
        state.player.health = bd:getOverallBodyHealth()

        -- Collect injuries from all body parts
        local injuries = {}
        local bodyParts = bd:getBodyParts()
        for i = 1, bodyParts:size() do
            local bp = bodyParts:get(i - 1)
            -- Condition check: ISHealthPanel.lua:516
            if bp:HasInjury() or bp:bandaged() or bp:getSplintFactor() > 0 then
                local partName = BodyPartType.ToString(bp:getType())
                local info = {part = partName}
                -- All methods verified: ISInventoryPaneContextMenu.lua:2790,
                -- ISHealthPanel.lua:234,516,660,765
                if bp:scratched() then info.scratched = true end
                if bp:isDeepWounded() then info.deep_wound = true end
                if bp:bitten() then info.bitten = true end
                if bp:bleeding() then info.bleeding = true end
                if bp:getFractureTime() > 0 then info.fracture = true end
                if bp:getSplintFactor() > 0 then info.splinted = true end
                if bp:bandaged() then info.bandaged = true end
                table.insert(injuries, info)
            end
        end
        if #injuries > 0 then
            state.player.injuries = injuries
        end
    end

    -- Player position — verified: ISBuildAction.lua, ISCampingMenu.lua
    state.player = state.player or {}
    state.player.position = {
        x = math.floor(player:getX()),
        y = math.floor(player:getY()),
        z = math.floor(player:getZ()),
    }

    -- Indoors check — verified: ISZoneDisplay.lua, ISWorldObjectContextMenu.lua
    state.player.indoors = not player:isOutside()

    -- Weather — verified in B42 client:
    --   getClimateManager(): ClimateColorsDebug.lua:16
    --   cm:getTemperature(): DailyValuesDebug.lua:195
    --   cm:getPrecipitationIntensity(): ClimateDebug.lua:185
    --   NOTE: RainManager not in B42 client code. getHumidity not confirmed
    --         on ClimateManager directly in B42 client. Only use verified methods.
    local climate = getClimateManager()
    if climate then
        state.weather = {
            temperature = climate:getTemperature(),
            precipitation = climate:getPrecipitationIntensity(),
        }
    end

    return state
end


-- OnTick handler: increment counter, check for responses periodically
function RTZ_Bridge.onTick()
    if not RTZ_Bridge._initialized then return end

    RTZ_Bridge._tick_count = RTZ_Bridge._tick_count + 1
    if RTZ_Bridge._tick_count < RTZ.POLL_INTERVAL_TICKS then return end
    RTZ_Bridge._tick_count = 0

    RTZ_Bridge.checkResponses()
end


-- Check for response files matching pending requests
function RTZ_Bridge.checkResponses()
    local now = getTimestampMs()

    -- Check pending chat responses
    for requestId, pending in pairs(RTZ_Bridge._pending) do
        -- Check for timeout
        if now - pending.sent_ms > RTZ.REQUEST_TIMEOUT_MS then
            print("[RTZ] Request timed out: " .. requestId)
            RTZ_Bridge._pending[requestId] = nil
        else
            -- Try to read response file
            local respFilename = RTZ.BRIDGE_PREFIX .. RTZ.RESP_PREFIX .. requestId .. ".json"

            -- Skip if we already processed this response
            if not RTZ_Bridge._processed[respFilename] then
                local response = RTZ_Bridge.readResponseFile(respFilename)
                if response then
                    RTZ_Bridge._processed[respFilename] = true
                    RTZ_Bridge._pending[requestId] = nil
                    RTZ_Bridge.handleResponse(response, pending.personality)
                end
            end
        end
    end

    -- Check for ambient push messages from daemon
    -- Debounce at 4 seconds — daemon deletes push file after 2 seconds,
    -- so 4 second gap ensures each file is read exactly once.
    -- getFileReader verified: ISLayoutManager.lua:127 (B42 client)
    if now - RTZ_Bridge._last_push_read > 4000 then
        local pushResponse = RTZ_Bridge.readResponseFile(RTZ.BRIDGE_PREFIX .. "rt_push.json")
        if pushResponse then
            RTZ_Bridge._last_push_read = now
            for _, msg in ipairs(pushResponse.messages or {}) do
                local pers = msg.personality or "system"
                local text = msg.text or ""
                print("[RTZ] " .. string.upper(pers) .. ": " .. text)
                if BusTerminalUI and BusTerminalUI.instance and BusTerminalUI.instance:isVisible() then
                    BusTerminalUI.instance:addMessage(pers, text)
                end
            end
        end
    end
end


-- Read and parse a response JSON file. Returns decoded table or nil.
function RTZ_Bridge.readResponseFile(filename)
    local ok, result = pcall(function()
        -- getFileReader(filename, createIfNull) — vanilla: ISLayoutManager.lua:132
        local reader = getFileReader(filename, false)
        if not reader then return nil end

        local lines = {}
        local line = reader:readLine()
        while line do
            table.insert(lines, line)
            line = reader:readLine()
        end
        reader:close()

        local content = table.concat(lines, "")
        if content == "" then return nil end

        return RTZ_JSON.decode(content)
    end)

    if ok then
        return result
    else
        print("[RTZ] ERROR reading response: " .. tostring(result))
        return nil
    end
end


-- Handle a decoded response from the daemon.
-- Routes to Terminal UI if open, always logs to console.
function RTZ_Bridge.handleResponse(response, personality)
    if not response or not response.messages then
        print("[RTZ] WARNING: Empty or malformed response")
        return
    end

    for _, msg in ipairs(response.messages) do
        local pers = msg.personality or personality or "unknown"
        local text = msg.text or "(no response)"

        -- Always log to console
        print("[RTZ] " .. string.upper(pers) .. ": " .. text)

        -- Route to Terminal UI if open
        if BusTerminalUI and BusTerminalUI.instance and BusTerminalUI.instance:isVisible() then
            BusTerminalUI.instance:addMessage(pers, text)
        end
    end
end


-- Register event hooks
Events.OnGameStart.Add(function()
    RTZ_Bridge.init()
end)

Events.OnTick.Add(function()
    RTZ_Bridge.onTick()
end)

-- Make globally accessible
_G.RTZ_Bridge = RTZ_Bridge
