-- Monster Capsule GB — Full Memory Dumper
-- Dumps WRAM, SRAM, VRAM, OAM, IO regs to files every 5 seconds
-- and on every state change (screen transition, battle start, etc)

local dump_dir = "/tmp/mcgb_dumps/"
os.execute("mkdir -p " .. dump_dir)

local frame = 0
local dump_count = 0
local prev_screen = -1
local prev_star_chips = -1

function dump_region(filename, start_addr, length)
    local f = io.open(dump_dir .. filename, "wb")
    for i = 0, length - 1 do
        f:write(string.char(emu:read8(start_addr + i)))
    end
    f:close()
end

function dump_all(reason)
    dump_count = dump_count + 1
    local prefix = string.format("%04d_%s", dump_count, reason)
    
    -- WRAM: C000-DFFF (8KB)
    dump_region(prefix .. "_wram.bin", 0xC000, 0x2000)
    
    -- SRAM: A000-BFFF (8KB) 
    dump_region(prefix .. "_sram.bin", 0xA000, 0x2000)
    
    -- VRAM: 8000-9FFF (8KB)
    dump_region(prefix .. "_vram.bin", 0x8000, 0x2000)
    
    -- OAM: FE00-FE9F (160 bytes)
    dump_region(prefix .. "_oam.bin", 0xFE00, 0xA0)
    
    -- IO Registers: FF00-FF7F (128 bytes)
    dump_region(prefix .. "_io.bin", 0xFF00, 0x80)
    
    -- HRAM: FF80-FFFE (127 bytes)
    dump_region(prefix .. "_hram.bin", 0xFF80, 0x7F)
    
    -- Log key values
    local log = io.open(dump_dir .. "log.txt", "a")
    local screen = emu:read8(0xC200)
    local chips = emu:read8(0xC2ED)
    local capsule_ct = emu:read8(0xC418)
    
    -- Read monster roster area from WRAM (C400-C500 might be runtime roster)
    local roster = ""
    for i = 0, 0xFF do
        roster = roster .. string.format("%02X ", emu:read8(0xC400 + i))
        if (i + 1) % 16 == 0 then roster = roster .. "\n    " end
    end
    
    log:write(string.format("\n=== Dump %d: %s (frame %d) ===\n", dump_count, reason, frame))
    log:write(string.format("  Screen: 0x%02X  StarChips: %d  CapsuleCount: %d\n", screen, chips, capsule_ct))
    log:write(string.format("  C400-C4FF:\n    %s\n", roster))
    
    -- Also dump the battle area
    if screen >= 0x04 and screen <= 0x09 then
        local battle = ""
        for i = 0, 35 do
            battle = battle .. string.format("%02X ", emu:read8(0xC69A + i))
        end
        log:write(string.format("  Battle data (C69A): %s\n", battle))
    end
    
    log:close()
    
    -- Write a status file I can poll
    local status = io.open(dump_dir .. "status.txt", "w")
    status:write(string.format("frame=%d\ndumps=%d\nscreen=0x%02X\nchips=%d\ncapsules=%d\nreason=%s\n",
        frame, dump_count, screen, chips, capsule_ct, reason))
    status:close()
end

function on_frame()
    frame = frame + 1
    
    local screen = emu:read8(0xC200)
    local chips = emu:read8(0xC2ED)
    
    -- Dump on screen change
    if screen ~= prev_screen then
        dump_all(string.format("screen_%02X_to_%02X", prev_screen, screen))
        prev_screen = screen
    end
    
    -- Dump on star chip change
    if chips ~= prev_star_chips and prev_star_chips >= 0 then
        dump_all(string.format("chips_%d_to_%d", prev_star_chips, chips))
        prev_star_chips = chips
    elseif prev_star_chips < 0 then
        prev_star_chips = chips
    end
    
    -- Periodic dump every 300 frames (5 seconds)
    if frame % 300 == 0 then
        dump_all("periodic")
    end
end

callbacks:add("frame", on_frame)

-- Initial dump
dump_all("init")

local status = io.open(dump_dir .. "status.txt", "w")
status:write("started=true\nframe=0\n")
status:close()

console:log("Memory dumper active. Outputs to " .. dump_dir)
