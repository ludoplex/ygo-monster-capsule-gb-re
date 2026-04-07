-- Monster Capsule GB WRAM watcher
-- Dumps key memory addresses every frame

local log_file = io.open("/tmp/mcgb_wram_log.txt", "w")

local frame = 0
local prev_star_chips = 0

function watch()
    frame = frame + 1
    if frame % 60 ~= 0 then return end  -- check once per second
    
    local star_chips = emu:read8(0xC2ED)
    local screen = emu:read8(0xC200)
    local capsule_count = emu:read8(0xC418)
    
    if star_chips ~= prev_star_chips then
        log_file:write(string.format("Frame %d: Star Chips changed: %d -> %d (screen=%02X)\n", 
            frame, prev_star_chips, star_chips, screen))
        log_file:flush()
        prev_star_chips = star_chips
    end
    
    -- Dump battle area when in battle
    if screen >= 0x04 and screen <= 0x06 then
        local battle_data = ""
        for i = 0, 35 do
            battle_data = battle_data .. string.format("%02X ", emu:read8(0xC69A + i))
        end
        log_file:write(string.format("Frame %d: BATTLE DATA: %s\n", frame, battle_data))
        log_file:flush()
    end
end

callbacks:add("frame", watch)
log_file:write("WRAM watcher started\n")
log_file:flush()
