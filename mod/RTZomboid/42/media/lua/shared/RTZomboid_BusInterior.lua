-- RT-Zomboid Bus Interior Override
-- Moves ATAApocalypseBus from the "bus" interior category (3x7)
-- to a custom "apocalypsebus" category using 4x12 colossal dimensions.
--
-- The global VehicleTypes table is defined in RVVehicleTypes.lua
-- (RV Interior mod, PROJECTRVInterior42).
-- Our mod.info has require=PROJECTRVInterior42 to ensure load order.
--
-- Room assignment key construction verified in RVServerMP_V3.lua:58-94:
--   "AssignedRooms" .. (typeKey == "normal" and "" or typeKey)
--   Dynamic, not hardcoded — our new type key will work.
--
-- Colossal category definition verified in RVVehicleTypes.lua:618-661.

local function removeFromScripts(typeKey, vehicleName)
    if not VehicleTypes or not VehicleTypes[typeKey] then return end
    local scripts = VehicleTypes[typeKey].scripts
    if not scripts then return end
    for i = #scripts, 1, -1 do
        if scripts[i] == vehicleName then
            table.remove(scripts, i)
        end
    end
end

local function setupApocalypseBusInterior()
    if not VehicleTypes then
        print("[RTZ] WARNING: VehicleTypes not found, RV Interior not loaded?")
        return
    end

    -- Remove ATAApocalypseBus from the bus category (3x7)
    -- Verified: RVVehicleTypes.lua line 370, bus scripts list
    removeFromScripts("bus", "Base.ATAApocalypseBus")

    -- Create custom category with colossal dimensions but rear/trunk entry
    -- All fields verified from colossal definition: RVVehicleTypes.lua:618-661
    VehicleTypes["apocalypsebus"] = {
        scripts = {
            "Base.ATAApocalypseBus",
        },
        rooms = (function()
            local t = {}
            -- Use slots 30-37 at colossal Y=12420 to reuse existing map data
            -- Colossal vehicles allocate from col 0, so no practical conflict
            -- Room coordinate formula: RVVehicleTypes.lua:636
            for col = 30, 37 do
                table.insert(t, { x = col * 60 + 22560, y = 12420, z = 0 })
            end
            return t
        end)(),
        offset = { x = 1, y = 1 },
        requiresSeat = false,
        requiresTrunk = true,
        -- trunkParts copied from colossal: RVVehicleTypes.lua:641-654
        trunkParts = {
            TrailerTrunk = true, BigTrunk = true, NormalTrunk = true,
            TrunkDoor = true, DoorRear = true, DoorRearLeft = true,
            DoorRearRight = true, TrunkDoor1 = true,
            TrailerTrunk1 = true, TrailerTrunk2 = true,
            TrailerTrunk3 = true, BigTrunk1 = true, BigTrunk2 = true,
            BigTrunk3 = true, SmallTrunk = true, SmallTrunk1 = true,
            SmallTrunk2 = true, SmallTrunk3 = true,
            VanSeatsTrunk2 = true, NormalTrunk1 = true,
            NormalTrunk2 = true, NormalTrunk3 = true,
            TruckBed = true, AnimalEntry = true,
            TrailerAnimalFood = true, ATSMegaTrunk = true,
            TrailerAnimalEggs = true,
        },
        genX = 0,
        genY = 0,
        genFloor = 1,
        roomWidth = 4,
        roomHeight = 12,
    }

    print("[RTZ] Apocalypse Bus interior: 4x12 (upgraded from 3x7)")
end

-- Events.OnGameStart verified: ISChat.lua:1186 (B42 client)
Events.OnGameStart.Add(setupApocalypseBusInterior)
