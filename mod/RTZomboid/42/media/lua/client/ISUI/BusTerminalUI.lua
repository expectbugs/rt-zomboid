-- Bus Terminal UI
-- ISCollapsableWindow with single "Bus Intelligence" chat panel.
-- Krang always responds. Eris occasionally pipes in.
-- Opened via F9 hotkey or /rtui chat command.
--
-- All UI APIs verified against B42 client source:
--   ISCollapsableWindow: ISUI/ISCollapsableWindow.lua:366 (new), :26 (createChildren)
--   ISRichTextPanel: ISUI/ISRichTextPanel.lua:689 (new), :12 (setText), :374 (paginate)
--   ISTextEntryBox: ISUI/ISTextEntryBox.lua:309 (new), :60 (getText), :105 (setText)
--   ISButton: ISUI/ISButton.lua:447 (new), :47 (onclick callback)
--   Text/scroll pattern: Chat/ISChat.lua:707-763
--   Scroll to bottom: setYScroll(-10000) -- ISChat.lua:762
--   addScrollBars: ISUIElement.lua:1205

require "ISUI/ISCollapsableWindow"
require "ISUI/ISRichTextPanel"
require "ISUI/ISTextEntryBox"
require "ISUI/ISButton"

BusTerminalUI = ISCollapsableWindow:derive("BusTerminalUI")

-- Singleton instance
BusTerminalUI.instance = nil

-- Colors for message senders (RGB 0-1)
BusTerminalUI.colors = {
    krang = {r = 0, g = 0.9, b = 0.3},     -- green
    eris = {r = 0.8, g = 0.2, b = 0.8},     -- purple
    player = {r = 1, g = 1, b = 1},          -- white
    system = {r = 1, g = 0.7, b = 0},        -- amber
}

-- Max lines before oldest are trimmed
BusTerminalUI.maxLines = 200


function BusTerminalUI:new(x, y, width, height)
    local o = ISCollapsableWindow:new(x, y, width, height)
    setmetatable(o, self)
    self.__index = self
    o.title = "Bus Intelligence"
    o:setResizable(true)
    o.minimumWidth = 500
    o.minimumHeight = 350
    o.chatLines = {}
    return o
end


function BusTerminalUI:createChildren()
    ISCollapsableWindow.createChildren(self)

    local titleBarH = self:titleBarHeight()
    local inset = 6
    local entryHeight = 28
    local btnWidth = 65
    local resizeH = self:resizeWidgetHeight()

    -- Message log — fills window above the entry row
    -- Leave room for: entry row + inset gaps + resize handle + extra padding
    local logY = titleBarH + inset
    local bottomPad = resizeH + inset
    local logH = self.height - titleBarH - entryHeight - inset * 3 - bottomPad
    self.messageLog = ISRichTextPanel:new(inset, logY, self.width - inset * 2, logH)
    self.messageLog:initialise()
    self.messageLog.defaultFont = UIFont.Medium
    self.messageLog.background = true
    self.messageLog.backgroundColor = {r = 0.02, g = 0.02, b = 0.02, a = 0.95}
    self.messageLog:setAnchorTop(true)
    self.messageLog:setAnchorLeft(true)
    self.messageLog:setAnchorRight(true)
    self.messageLog:setAnchorBottom(true)
    self.messageLog:addScrollBars()
    self.messageLog.autosetheight = false
    self.messageLog.marginLeft = 8
    self.messageLog.marginTop = 8
    self.messageLog.marginRight = 8
    self:addChild(self.messageLog)

    -- Text entry — below the message log, above the resize handle
    local entryY = logY + logH + inset
    local entryW = self.width - btnWidth - inset * 3
    self.textEntry = ISTextEntryBox:new("", inset, entryY, entryW, entryHeight)
    self.textEntry.font = UIFont.Medium
    self.textEntry:initialise()
    self.textEntry:instantiate()
    self.textEntry.backgroundColor = {r = 0.1, g = 0.1, b = 0.1, a = 0.9}
    self.textEntry:setAnchorBottom(true)
    self.textEntry:setAnchorLeft(true)
    self.textEntry:setAnchorRight(true)
    self.textEntry:setAnchorTop(false)
    self:addChild(self.textEntry)

    -- Enter key sends message
    local ui = self
    self.textEntry.onCommandEntered = function()
        ui:onSend()
    end

    -- Send button — right of text entry
    local btnX = entryW + inset * 2
    self.sendBtn = ISButton:new(btnX, entryY, btnWidth, entryHeight, "SEND", self,
        BusTerminalUI.onSendClicked)
    self.sendBtn:initialise()
    self.sendBtn:setAnchorBottom(true)
    self.sendBtn:setAnchorRight(true)
    self.sendBtn:setAnchorLeft(false)
    self.sendBtn:setAnchorTop(false)
    self.sendBtn.borderColor = {r = 0.3, g = 0.8, b = 0.3, a = 0.8}
    self:addChild(self.sendBtn)
end


-- ISButton onclick: self.onclick(self.target, self, ...) — ISButton.lua:47
function BusTerminalUI:onSendClicked(button)
    self:onSend()
end


function BusTerminalUI:onSend()
    local text = self.textEntry:getText()
    if not text or text == "" then return end

    self.textEntry:setText("")

    -- Show player message in log
    self:addMessage("player", text)

    -- Send to daemon — always addressed to krang
    -- Daemon handles routing (Krang always responds, Eris sometimes)
    if RTZ_Bridge and RTZ_Bridge.sendRequest then
        RTZ_Bridge.sendRequest(RTZ.REQUEST_TYPES.CHAT, "krang", text)
    end
end


-- Add a message to the chat log with color
function BusTerminalUI:addMessage(sender, text)
    local color = BusTerminalUI.colors[sender] or BusTerminalUI.colors.system
    local colorTag = "<RGB:" .. color.r .. "," .. color.g .. "," .. color.b .. ">"

    local prefix = ""
    if sender == "player" then
        prefix = colorTag .. "> "
    elseif sender == "system" then
        prefix = colorTag .. "[SYSTEM] "
    elseif sender == "krang" then
        prefix = colorTag .. "KRANG: "
    elseif sender == "eris" then
        prefix = colorTag .. "ERIS: "
    else
        prefix = colorTag .. string.upper(sender) .. ": "
    end

    local line = prefix .. text .. " <LINE> "

    -- Store and trim — pattern from ISChat.lua:738-748
    table.insert(self.chatLines, line)
    if #self.chatLines > BusTerminalUI.maxLines then
        local newLines = {}
        for i = 2, #self.chatLines do
            table.insert(newLines, self.chatLines[i])
        end
        self.chatLines = newLines
    end

    -- Rebuild text — pattern from ISChat.lua:750-758
    local newText = ""
    for i, v in ipairs(self.chatLines) do
        if i == #self.chatLines then
            v = string.gsub(v, " <LINE> $", "")
        end
        newText = newText .. v
    end

    self.messageLog:setText(newText)
    self.messageLog:paginate()
    self.messageLog:setYScroll(-10000)
end


-- Toggle the terminal window
function BusTerminalUI.toggle()
    if BusTerminalUI.instance and BusTerminalUI.instance:isVisible() then
        BusTerminalUI.instance:setVisible(false)
        BusTerminalUI.instance:removeFromUIManager()
        BusTerminalUI.instance = nil
        return
    end

    if BusTerminalUI.instance then
        BusTerminalUI.instance:setVisible(true)
        return
    end

    -- Center on screen — getCore() verified throughout vanilla
    local sw = getCore():getScreenWidth()
    local sh = getCore():getScreenHeight()
    local w = 700
    local h = 500
    local x = (sw - w) / 2
    local y = (sh - h) / 2

    local ui = BusTerminalUI:new(x, y, w, h)
    ui:initialise()
    ui:addToUIManager()
    ui:setVisible(true)

    BusTerminalUI.instance = ui

    ui:addMessage("system", "Bus Intelligence online. Type a message below.")
end


_G.BusTerminalUI = BusTerminalUI
