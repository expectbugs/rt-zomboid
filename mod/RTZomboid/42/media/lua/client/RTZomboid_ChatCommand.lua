-- RT-Zomboid Hotkey and Chat Command Handler
-- F9 toggles Bus Terminal UI.
-- /rtui, /krang, /eris available in multiplayer chat.
--
-- Events.OnKeyPressed: ISChat.lua:1178, ISSearchManager.lua:1476
-- Keyboard constants: keyBinding.lua (F7/F9/F12 unbound in vanilla)

-- Hotkey: F9 to toggle terminal
local function onKeyPressed(key)
    if key == Keyboard.KEY_F9 then
        BusTerminalUI.toggle()
    end
end

Events.OnKeyPressed.Add(onKeyPressed)

-- Multiplayer chat commands (ISChat only exists in MP)
local function hookChatCommands()
    if not ISChat or not ISChat.onCommandEntered then
        print("[RTZ] Singleplayer mode - chat commands not available (use F9)")
        return
    end

    local originalOnCommandEntered = ISChat.onCommandEntered

    ISChat.onCommandEntered = function(self)
        local text = ISChat.instance.textEntry:getText()
        if not text or text == "" then
            originalOnCommandEntered(self)
            return
        end

        if text == "/rtui" then
            ISChat.instance.textEntry:setText("")
            ISChat.instance:unfocus()
            BusTerminalUI.toggle()
            return
        end

        if luautils.stringStarts(text, "/krang ") or luautils.stringStarts(text, "/eris ") then
            local message = string.sub(text, 8)
            if luautils.stringStarts(text, "/eris ") then
                message = string.sub(text, 7)
            end
            ISChat.instance.textEntry:setText("")
            ISChat.instance:unfocus()
            if message ~= "" then
                if not BusTerminalUI.instance or not BusTerminalUI.instance:isVisible() then
                    BusTerminalUI.toggle()
                end
                if BusTerminalUI.instance then
                    BusTerminalUI.instance:addMessage("player", message)
                    if RTZ_Bridge and RTZ_Bridge.sendRequest then
                        RTZ_Bridge.sendRequest(RTZ.REQUEST_TYPES.CHAT, "krang", message)
                    end
                end
            end
            return
        end

        originalOnCommandEntered(self)
    end

    print("[RTZ] Multiplayer chat commands registered: /rtui, /krang, /eris")
end

Events.OnGameStart.Add(hookChatCommands)

print("[RTZ] Hotkey registered: F9 = toggle terminal")
