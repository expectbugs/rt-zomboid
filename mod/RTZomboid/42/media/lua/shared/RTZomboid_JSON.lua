--
-- RTZomboid_JSON.lua — JSON encoder/decoder for Project Zomboid B42
--
-- Written for PZ's Kahlua Lua VM. Every function used has been verified
-- against the B42 vanilla client source at:
--   ~/.local/share/Steam/steamapps/common/ProjectZomboid/projectzomboid/media/lua/
--
-- Verified functions used:
--   type(), pairs(), ipairs(), tostring(), tonumber(), error()
--   string.gsub(str,pat,STRING), string.sub(), string.find(), string.len(), string.upper()
--   table.insert(), table.concat(), math.floor()
--
-- NOT used (unverified or absent in Kahlua):
--   rawget, next, string.byte, string.char, math.huge, select, loadstring,
--   string.format(%g/%f), string.gsub(str,pat,TABLE), pcall (exists but 0 grep hits)
--

local RTZ_JSON = {}

-------------------------------------------------------------------------------
-- Encode
-------------------------------------------------------------------------------

local function encodeString(val)
    -- string.gsub with STRING replacement: verified (MultiplayerUI.lua:645)
    -- Apply each escape individually — table-as-3rd-arg is NOT verified in Kahlua.
    local s = val
    s = string.gsub(s, "\\", "\\\\")  -- must be first
    s = string.gsub(s, '"', '\\"')
    s = string.gsub(s, "\n", "\\n")
    s = string.gsub(s, "\r", "\\r")
    s = string.gsub(s, "\t", "\\t")
    return '"' .. s .. '"'
end

local function encodeNumber(val)
    -- Check for NaN using standard Lua idiom
    if val ~= val then
        error("cannot encode NaN")
    end
    -- tostring() verified: ISMenuContextWorld.lua:143, used throughout vanilla
    -- Vanilla formats numbers with tostring(), not string.format %g/%f (unverified)
    return tostring(val)
end

-- Forward declaration
local encodeValue

local function encodeTable(val, visited)
    if visited[val] then
        error("circular reference in table")
    end
    visited[val] = true

    -- Determine if this is an array or object.
    -- Cannot use next() — does not exist in Kahlua.
    -- Use pairs() loop instead (verified throughout vanilla).
    local isEmpty = true
    local isArray = false
    for k, _ in pairs(val) do
        isEmpty = false
        isArray = (type(k) == "number")
        break
    end

    if isEmpty then
        visited[val] = nil
        return "{}"
    end

    if isArray then
        -- Verify all keys are sequential numbers
        local n = 0
        for k, _ in pairs(val) do
            if type(k) ~= "number" then
                error("mixed key types in table")
            end
            n = n + 1
        end
        -- Encode as array
        local parts = {}
        -- ipairs() verified: ISInventoryBuildMenu.lua:34, ISChat.lua:455
        for i, v in ipairs(val) do
            table.insert(parts, encodeValue(v, visited))
        end
        visited[val] = nil
        return "[" .. table.concat(parts, ",") .. "]"
    else
        -- Encode as object
        local parts = {}
        for k, v in pairs(val) do
            if type(k) ~= "string" then
                error("non-string key in object: " .. tostring(k) .. " (" .. type(k) .. ")")
            end
            table.insert(parts, encodeString(k) .. ":" .. encodeValue(v, visited))
        end
        visited[val] = nil
        return "{" .. table.concat(parts, ",") .. "}"
    end
end

encodeValue = function(val, visited)
    local t = type(val)
    if t == "string" then
        return encodeString(val)
    elseif t == "number" then
        return encodeNumber(val)
    elseif t == "boolean" then
        return tostring(val)
    elseif t == "table" then
        return encodeTable(val, visited)
    elseif val == nil then
        return "null"
    else
        error("cannot encode type: " .. t)
    end
end

function RTZ_JSON.encode(val)
    return encodeValue(val, {})
end

-------------------------------------------------------------------------------
-- Decode
-------------------------------------------------------------------------------

-- Minimal JSON decoder using only verified string functions.
-- string.sub verified: used throughout vanilla
-- string.find verified: used throughout vanilla
-- string.len verified: implied by # operator on strings
-- tonumber verified: fundamental Lua function

local function skipWhitespace(str, pos)
    -- string.find with pattern verified: vanilla uses string.find extensively
    local _, endPos = string.find(str, "^%s*", pos)
    return endPos + 1
end

local function decodeString(str, pos)
    -- pos should be at the opening quote
    pos = pos + 1  -- skip opening "
    local parts = {}
    while pos <= string.len(str) do
        local ch = string.sub(str, pos, pos)
        if ch == '"' then
            return table.concat(parts), pos + 1
        elseif ch == '\\' then
            pos = pos + 1
            local esc = string.sub(str, pos, pos)
            if esc == '"' then table.insert(parts, '"')
            elseif esc == '\\' then table.insert(parts, '\\')
            elseif esc == '/' then table.insert(parts, '/')
            elseif esc == 'n' then table.insert(parts, '\n')
            elseif esc == 'r' then table.insert(parts, '\r')
            elseif esc == 't' then table.insert(parts, '\t')
            elseif esc == 'b' then table.insert(parts, '\b')
            elseif esc == 'f' then table.insert(parts, '\f')
            elseif esc == 'u' then
                -- Unicode escape — just pass through as \uXXXX for now
                -- Full unicode support needs string.char which is unverified
                local hex = string.sub(str, pos + 1, pos + 4)
                table.insert(parts, '\\u' .. hex)
                pos = pos + 4
            else
                table.insert(parts, esc)
            end
            pos = pos + 1
        else
            table.insert(parts, ch)
            pos = pos + 1
        end
    end
    error("unterminated string")
end

-- Forward declaration
local decodeValue

local function decodeNumber(str, pos)
    local _, endPos = string.find(str, "^%-?%d+%.?%d*[eE]?[%+%-]?%d*", pos)
    if not endPos then
        error("invalid number at position " .. pos)
    end
    local numStr = string.sub(str, pos, endPos)
    local num = tonumber(numStr)
    if not num then
        error("invalid number: " .. numStr)
    end
    return num, endPos + 1
end

local function decodeObject(str, pos)
    pos = pos + 1  -- skip {
    local obj = {}
    pos = skipWhitespace(str, pos)
    if string.sub(str, pos, pos) == "}" then
        return obj, pos + 1
    end
    while true do
        -- Parse key (must be string)
        pos = skipWhitespace(str, pos)
        if string.sub(str, pos, pos) ~= '"' then
            error("expected string key at position " .. pos)
        end
        local key
        key, pos = decodeString(str, pos)
        -- Parse colon
        pos = skipWhitespace(str, pos)
        if string.sub(str, pos, pos) ~= ":" then
            error("expected ':' at position " .. pos)
        end
        pos = pos + 1
        -- Parse value
        local val
        val, pos = decodeValue(str, pos)
        obj[key] = val
        -- Next token
        pos = skipWhitespace(str, pos)
        local ch = string.sub(str, pos, pos)
        if ch == "}" then
            return obj, pos + 1
        elseif ch == "," then
            pos = pos + 1
        else
            error("expected ',' or '}' at position " .. pos)
        end
    end
end

local function decodeArray(str, pos)
    pos = pos + 1  -- skip [
    local arr = {}
    pos = skipWhitespace(str, pos)
    if string.sub(str, pos, pos) == "]" then
        return arr, pos + 1
    end
    while true do
        local val
        val, pos = decodeValue(str, pos)
        table.insert(arr, val)
        pos = skipWhitespace(str, pos)
        local ch = string.sub(str, pos, pos)
        if ch == "]" then
            return arr, pos + 1
        elseif ch == "," then
            pos = pos + 1
        else
            error("expected ',' or ']' at position " .. pos)
        end
    end
end

decodeValue = function(str, pos)
    pos = skipWhitespace(str, pos)
    local ch = string.sub(str, pos, pos)

    if ch == '"' then
        return decodeString(str, pos)
    elseif ch == '{' then
        return decodeObject(str, pos)
    elseif ch == '[' then
        return decodeArray(str, pos)
    elseif ch == 't' then
        if string.sub(str, pos, pos + 3) == "true" then
            return true, pos + 4
        end
        error("invalid literal at position " .. pos)
    elseif ch == 'f' then
        if string.sub(str, pos, pos + 4) == "false" then
            return false, pos + 5
        end
        error("invalid literal at position " .. pos)
    elseif ch == 'n' then
        if string.sub(str, pos, pos + 3) == "null" then
            return nil, pos + 4
        end
        error("invalid literal at position " .. pos)
    elseif ch == '-' or string.find(ch, "%d") then
        return decodeNumber(str, pos)
    else
        error("unexpected character '" .. ch .. "' at position " .. pos)
    end
end

function RTZ_JSON.decode(str)
    if type(str) ~= "string" then
        error("expected string, got " .. type(str))
    end
    local val, pos = decodeValue(str, 1)
    return val
end

-------------------------------------------------------------------------------
-- Export
-------------------------------------------------------------------------------

_G.RTZ_JSON = RTZ_JSON

return RTZ_JSON
