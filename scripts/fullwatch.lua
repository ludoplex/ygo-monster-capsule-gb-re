-- Full memory watcher — every frame, all modes
-- Distinguishes: Overworld, Menu, Battle Prep, Battle, Battle Action, Cutscene

local log = io.open("/tmp/mcgb_fullwatch.txt", "w")
log:setvbuf("line")

local frame = 0
local prev = {}
local prev_screen = -1
local mode_names = {
    [0x00] = "TITLE",
    [0x01] = "OVERWORLD",
    [0x02] = "TRANSITION",
    [0x03] = "MENU/DIALOG",
    [0x04] = "BATTLE_PREP",
    [0x05] = "BATTLE_GRID",
    [0x06] = "BATTLE_??",
    [0x07] = "BATTLE_ACTION",
    [0x08] = "BATTLE_??2",
    [0x09] = "BATTLE_RESULT",
}

-- Watch ALL interesting WRAM regions
local regions = {
    -- Core state
    {name="screen",     addr=0xC200, len=16},
    {name="starchips",  addr=0xC2ED, len=1},
    {name="capsule_ct", addr=0xC418, len=1},
    
    -- Player state
    {name="player",     addr=0xC190, len=32},
    {name="inventory",  addr=0xC1E0, len=48},
    
    -- Monster roster (runtime)
    {name="roster_hdr", addr=0xC830, len=32},
    {name="roster_mon", addr=0xC850, len=160},
    
    -- Battle system
    {name="grid",       addr=0xC69A, len=36},
    {name="bctl",       addr=0xC680, len=26},
    {name="bturn",      addr=0xC6BE, len=32},
    {name="board_dat",  addr=0xC6E0, len=64},
    {name="bvals",      addr=0xC733, len=16},
    {name="bdmg",       addr=0xC750, len=48},
    {name="bhit",       addr=0xC7E0, len=48},
    {name="bcombat",    addr=0xC80C, len=32},
    
    -- Map/overworld
    {name="map",        addr=0xC300, len=32},
    {name="position",   addr=0xC23C, len=20},
    
    -- SRAM writes (save related)
    {name="sram_head",  addr=0xA000, len=16},
    {name="sram_chips", addr=0xA709, len=1},
    {name="sram_caps",  addr=0xB0A1, len=4},
    
    -- RNG
    {name="rng",        addr=0xC2E8, len=8},
    
    -- Dialog/text
    {name="dialog",     addr=0xC430, len=32},
    
    -- Capsule machine
    {name="capsule_m",  addr=0xC44A, len=32},
    
    -- Monster data at C500 area
    {name="mondat_50",  addr=0xC4FF, len=32},
    {name="mondat_5D",  addr=0xC5DA, len=32},
    
    -- IO/input
    {name="input",      addr=0xFFA9, len=1},
}

-- Initialize all previous values
for _, r in ipairs(regions) do
    prev[r.name] = {}
    for i = 0, r.len - 1 do
        local ok, val = pcall(function() return emu:read8(r.addr + i) end)
        prev[r.name][i] = ok and val or 0
    end
end

function get_mode(screen)
    return mode_names[screen] or string.format("UNK_%02X", screen)
end

function on_frame()
    frame = frame + 1
    
    local screen = emu:read8(0xC200)
    
    -- Log mode changes
    if screen ~= prev_screen then
        local old_mode = get_mode(prev_screen)
        local new_mode = get_mode(screen)
        log:write(string.format("\n### F%07d MODE: %s → %s ###\n", frame, old_mode, new_mode))
        
        -- On battle start, dump full roster
        if screen >= 0x04 and screen <= 0x09 and (prev_screen < 0x04 or prev_screen > 0x09) then
            log:write("  ROSTER:\n")
            for offset = 0x850, 0x8E0, 14 do
                local ok, marker = pcall(function() return emu:read8(0xC000 + offset) end)
                if ok and (marker == 0xC0 or marker == 0x60) then
                    local id = emu:read8(0xC000 + offset + 1)
                    local lv = emu:read8(0xC000 + offset + 2)
                    local exp = emu:read8(0xC000 + offset + 3)
                    local hp = emu:read8(0xC000 + offset + 4)
                    local atk = emu:read8(0xC000 + offset + 6)
                    local def = emu:read8(0xC000 + offset + 7)
                    local spd = emu:read8(0xC000 + offset + 8)
                    local side = marker == 0xC0 and "PLR" or "NPC"
                    log:write(string.format("    [%s] ID=%02X Lv%d EXP=%d HP=%d ATK=%d DEF=%d SPD=%d\n",
                        side, id, lv, exp, hp, atk, def, spd))
                end
            end
        end
        prev_screen = screen
    end
    
    -- Poll all regions for changes
    local mode = get_mode(screen)
    for _, r in ipairs(regions) do
        for i = 0, r.len - 1 do
            local ok, val = pcall(function() return emu:read8(r.addr + i) end)
            if ok and val ~= prev[r.name][i] then
                log:write(string.format("F%07d [%-13s] %04X %-11s +%02X: %02X→%02X (%3d→%3d)\n",
                    frame, mode, r.addr + i, r.name, i, prev[r.name][i], val, prev[r.name][i], val))
                prev[r.name][i] = val
            end
        end
    end
end

callbacks:add("frame", on_frame)
log:write("=== FULL MEMORY WATCHER STARTED ===\n")
log:write(string.format("Watching %d regions, every frame\n", #regions))
console:log("Full watcher active → /tmp/mcgb_fullwatch.txt")
console:log("Watching " .. #regions .. " regions across ALL game modes")
