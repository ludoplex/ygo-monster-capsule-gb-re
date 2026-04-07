-- Real-time memory stream — like tcpdump for the Game Boy bus
-- Outputs to stdout (visible in mGBA scripting console) 
-- and to a FIFO pipe that Claude can tail

local pipe_path = "/tmp/mgba_memstream"
os.execute("rm -f " .. pipe_path)
os.execute("mkfifo " .. pipe_path)

-- Open the pipe in non-blocking write mode
-- (use regular file as fallback since FIFO can block)
local logfile = io.open("/tmp/mgba_memstream.txt", "w")
logfile:setvbuf("line")  -- flush every line

local frame = 0
local watch_regions = {
    {name="StarChips", addr=0xC2ED, len=1, prev={}},
    {name="Screen", addr=0xC200, len=1, prev={}},
    {name="Capsules", addr=0xC418, len=1, prev={}},
    {name="BattleHP", addr=0xC7E5, len=1, prev={}},
    {name="MonRoster_00", addr=0xC400, len=64, prev={}},
    {name="MonRoster_40", addr=0xC440, len=64, prev={}},
    {name="MonRoster_80", addr=0xC480, len=64, prev={}},
    {name="MonRoster_C0", addr=0xC4C0, len=64, prev={}},
    {name="BattleState", addr=0xC69A, len=36, prev={}},
    {name="SRAM_head", addr=0xA000, len=32, prev={}},
    {name="SRAM_4000", addr=0xE000, len=32, prev={}},  -- SRAM mirror in WRAM
}

-- Initialize previous values
for _, region in ipairs(watch_regions) do
    for i = 0, region.len - 1 do
        region.prev[i] = emu:read8(region.addr + i)
    end
end

function check_changes()
    frame = frame + 1
    if frame % 2 ~= 0 then return end  -- check every other frame (~30Hz)
    
    for _, region in ipairs(watch_regions) do
        for i = 0, region.len - 1 do
            local val = emu:read8(region.addr + i)
            if val ~= region.prev[i] then
                local line = string.format("F%07d %04X %-15s [+%02X] %02X→%02X",
                    frame, region.addr + i, region.name, i, region.prev[i], val)
                logfile:write(line .. "\n")
                console:log(line)
                region.prev[i] = val
            end
        end
    end
end

callbacks:add("frame", check_changes)
logfile:write("=== MEMSTREAM STARTED ===\n")
logfile:flush()
console:log("Memory stream active → /tmp/mgba_memstream.txt")
console:log("Watching " .. #watch_regions .. " regions, ~30Hz polling")
