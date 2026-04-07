-- Capsule Machine Watcher
-- Captures machine selection, RNG state, and result every frame

local log = io.open("/tmp/mcgb_capsule_test.txt", "w")
log:setvbuf("line")

local frame = 0
local prev = {}

-- Watch broader SRAM area + capsule-related WRAM
local regions = {
    {name="screen",    addr=0xC200, len=1},
    {name="starchips", addr=0xC2ED, len=1},
    {name="capsule_ct",addr=0xC418, len=1},
    {name="rng",       addr=0xC2E8, len=8},
    {name="input",     addr=0xFFA9, len=1},
    -- Capsule machine area
    {name="cap_mach",  addr=0xC44A, len=48},
    {name="cap_data",  addr=0xC4FF, len=48},
    -- Broad SRAM scan for capsule tables
    {name="sram_B0",   addr=0xB0A0, len=16},
    {name="sram_B1",   addr=0xB0B0, len=16},
    {name="sram_B0C",  addr=0xB0C0, len=16},
    {name="sram_B0D",  addr=0xB0D0, len=16},
    {name="sram_B0E",  addr=0xB0E0, len=16},
    {name="sram_B0F",  addr=0xB0F0, len=16},
    {name="sram_B10",  addr=0xB100, len=32},
    {name="sram_B12",  addr=0xB120, len=32},
    {name="sram_B14",  addr=0xB140, len=32},
    -- Dialog area (shows monster name after pull)
    {name="dialog",    addr=0xC430, len=32},
    -- Monster roster (to see what gets added)
    {name="roster",    addr=0xC850, len=32},
    -- SRAM header (changes during save)
    {name="sram_hdr",  addr=0xA000, len=16},
    {name="sram_A7",   addr=0xA700, len=16},
}

for _, r in ipairs(regions) do
    prev[r.name] = {}
    for i = 0, r.len - 1 do
        local ok, val = pcall(function() return emu:read8(r.addr + i) end)
        prev[r.name][i] = ok and val or 0
    end
end

function on_frame()
    frame = frame + 1
    local screen = emu:read8(0xC200)
    
    for _, r in ipairs(regions) do
        for i = 0, r.len - 1 do
            local ok, val = pcall(function() return emu:read8(r.addr + i) end)
            if ok and val ~= prev[r.name][i] then
                log:write(string.format("F%07d %04X %-11s +%02X: %02X→%02X (%3d→%3d)\n",
                    frame, r.addr + i, r.name, i, prev[r.name][i], val, prev[r.name][i], val))
                prev[r.name][i] = val
            end
        end
    end
end

-- Also dump the full SRAM capsule area at startup for reference
log:write("=== CAPSULE MACHINE WATCHER ===\n")
log:write("=== SRAM B0A0-B150 initial state ===\n")
for addr = 0xB0A0, 0xB150, 16 do
    local hex = ""
    for i = 0, 15 do
        hex = hex .. string.format("%02X ", emu:read8(addr + i))
    end
    log:write(string.format("  %04X: %s\n", addr, hex))
end
log:write("\n")

callbacks:add("frame", on_frame)
console:log("Capsule watcher active → /tmp/mcgb_capsule_test.txt")
