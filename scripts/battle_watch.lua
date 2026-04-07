-- Battle system watcher — polls every frame during combat
-- Captures dice rolls, damage, position changes, turn state

local log = io.open("/tmp/mcgb_battle.txt", "w")
log:setvbuf("line")

local frame = 0
local prev = {}
local in_battle = false

-- Track these every frame during battle
local watches = {
    {name="screen",   addr=0xC200, len=1},
    {name="starchip", addr=0xC2ED, len=1},
    {name="hitprob",  addr=0xC7E5, len=1},
    {name="battlev",  addr=0xC733, len=8},
    {name="grid",     addr=0xC69A, len=36},
    {name="dmg_area", addr=0xC7E0, len=32},
    {name="combat",   addr=0xC80C, len=16},
    -- Monster HP tracking (byte 4 of each 14-byte record at C850+)
    {name="mon1_hp",  addr=0xC854, len=1},
    {name="mon2_hp",  addr=0xC862+4, len=1},
    {name="mon3_hp",  addr=0xC870+8, len=1},
    {name="mon4_hp",  addr=0xC8AD+4, len=1},
    {name="npc1_hp",  addr=0xC8CC+4, len=1},
    -- Turn state
    {name="turn",     addr=0xC680, len=16},
    {name="action",   addr=0xC6BE, len=16},
    -- Possible dice/RNG
    {name="rng1",     addr=0xC190, len=16},
    {name="rng2",     addr=0xC1A0, len=16},
}

-- Initialize
for _, w in ipairs(watches) do
    prev[w.name] = {}
    for i = 0, w.len - 1 do
        prev[w.name][i] = 0
    end
end

function on_frame()
    frame = frame + 1
    
    local screen = emu:read8(0xC200)
    
    -- Only do per-frame polling during battle screens (04, 05, 07)
    if screen >= 0x04 and screen <= 0x09 then
        if not in_battle then
            in_battle = true
            log:write(string.format("\n=== BATTLE START frame %d ===\n", frame))
            -- Dump full monster roster
            for offset = 0x850, 0x8E0, 14 do
                local marker = emu:read8(0xC000 + offset)
                if marker == 0xC0 or marker == 0x60 then
                    local id = emu:read8(0xC000 + offset + 1)
                    local lv = emu:read8(0xC000 + offset + 2)
                    local exp = emu:read8(0xC000 + offset + 3)
                    local hp = emu:read8(0xC000 + offset + 4)
                    local atk = emu:read8(0xC000 + offset + 6)
                    local def = emu:read8(0xC000 + offset + 7)
                    local spd = emu:read8(0xC000 + offset + 8)
                    local side = marker == 0xC0 and "PLR" or "NPC"
                    log:write(string.format("  [%s] ID=%02X Lv%d EXP=%d HP=%d ATK=%d DEF=%d SPD=%d\n",
                        side, id, lv, exp, hp, atk, def, spd))
                end
            end
        end
        
        -- Check for changes every frame
        for _, w in ipairs(watches) do
            for i = 0, w.len - 1 do
                local val = emu:read8(w.addr + i)
                if val ~= prev[w.name][i] then
                    log:write(string.format("F%07d %04X %-10s [+%02X] %02X→%02X (%d→%d)\n",
                        frame, w.addr + i, w.name, i, prev[w.name][i], val, prev[w.name][i], val))
                    prev[w.name][i] = val
                end
            end
        end
    else
        if in_battle then
            in_battle = false
            log:write(string.format("=== BATTLE END frame %d ===\n\n", frame))
        end
    end
end

callbacks:add("frame", on_frame)
log:write("=== BATTLE WATCHER STARTED ===\n")
console:log("Battle watcher active → /tmp/mcgb_battle.txt")
console:log("Per-frame polling during battle screens (04-09)")
