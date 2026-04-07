#!/usr/bin/env python3
"""Yu-Gi-Oh! Monster Capsule GB — Save Editor v2
Based on binary diff analysis of known save states."""

import sys
import shutil
from pathlib import Path

SAVE_PATH = Path.home() / "snap/retroarch/common/.config/retroarch/saves/mGBA/Yu-Gi-Oh! Monster Capsule GB (English).srm"

# Confirmed offsets from diff analysis
STAR_CHIPS = 0x6374
MONSTER_COUNT = 0x0204
MONSTER_ROSTER = 0x4000       # 14 bytes per record, 0x80 marker
MONSTER_ROSTER_MIRROR = 0x64A8  # mirror offset delta = 0x24A8
LEVEL_BYTE = 0x101C           # at least one monster level here
LEVEL_BYTE_MIRROR = 0x63E0
STATS_BLOCK = 0x10A0
STATS_BLOCK_MIRROR = 0x6463   # approximate mirror

# Monster record: 80 [ID] [byte2] [Level] [S1] [00] [S2] [S3] [S4] [00] [byte10] [byte11] [byte12] [byte13]
RECORD_SIZE = 14
RECORD_MARKER = 0x80

def read_save(path):
    with open(path, 'rb') as f:
        return bytearray(f.read())

def write_save(path, data):
    with open(path, 'wb') as f:
        f.write(data)

def parse_roster(data, base):
    """Parse monster records starting at base."""
    monsters = []
    i = base
    while i < base + 0x200:
        if data[i] == RECORD_MARKER and data[i+1] != 0xFF and data[i+1] != 0x80:
            rec = data[i:i+RECORD_SIZE]
            monsters.append({
                'offset': i,
                'id': rec[1],
                'byte2': rec[2],
                'level': rec[3],
                'stats': [rec[4], rec[5], rec[6], rec[7], rec[8]],
                'raw': bytes(rec),
            })
            i += RECORD_SIZE
        elif data[i] == 0xFF:
            break
        else:
            i += 1
    return monsters

def max_roster(data, base, max_level=99, max_stat=99):
    """Max out all existing monsters at the given roster base."""
    monsters = parse_roster(data, base)
    for m in monsters:
        off = m['offset']
        data[off + 3] = max_level      # Level
        data[off + 4] = max_stat       # Stat 1
        data[off + 6] = max_stat       # Stat 2
        data[off + 7] = max_stat       # Stat 3
        data[off + 8] = max_stat       # Stat 4
    return monsters

def add_monster(data, base, monster_id, level=99, stats=None):
    """Add a monster record at the given offset."""
    if stats is None:
        stats = [99, 0, 99, 99, 99]
    data[base] = RECORD_MARKER
    data[base + 1] = monster_id
    data[base + 2] = 0x01
    data[base + 3] = level
    data[base + 4] = stats[0]
    data[base + 5] = stats[1]
    data[base + 6] = stats[2]
    data[base + 7] = stats[3]
    data[base + 8] = stats[4]
    data[base + 9] = 0x00
    data[base + 10] = 0x31   # common value from existing records
    data[base + 11] = monster_id
    data[base + 12] = 0x63   # max
    data[base + 13] = 0xFF
    return data

if __name__ == '__main__':
    save_path = sys.argv[1] if len(sys.argv) > 1 else str(SAVE_PATH)
    
    print("=== Monster Capsule GB Save Editor v2 ===")
    print(f"Save: {save_path}")
    print()
    
    # Backup
    backup = save_path + '.v2backup'
    shutil.copy2(save_path, backup)
    print(f"Backup: {backup}")
    
    data = read_save(save_path)
    
    # 1. Max star chips
    old_chips = data[STAR_CHIPS]
    data[STAR_CHIPS] = 99
    print(f"\nStar Chips: {old_chips} → 99 (offset 0x{STAR_CHIPS:04X})")
    
    # 2. Max existing monsters at 0x4000
    print("\n--- Maxing existing roster (0x4000) ---")
    monsters = max_roster(data, MONSTER_ROSTER)
    for m in monsters:
        print(f"  Monster ID {m['id']:3d}: Lv{m['level']} → Lv99, stats maxed")
    
    # 3. Add new monsters to fill out the collection
    existing_ids = {m['id'] for m in monsters}
    next_slot = MONSTER_ROSTER + len(monsters) * RECORD_SIZE
    added = 0
    
    print(f"\n--- Adding missing monsters ---")
    # Add monsters with IDs 1-80 that aren't already owned
    for mid in range(1, 81):
        if mid not in existing_ids:
            data = add_monster(data, next_slot, mid)
            added += 1
            next_slot += RECORD_SIZE
            if next_slot >= MONSTER_ROSTER + 0x400:  # safety limit
                break
    print(f"  Added {added} new monsters (total: {len(monsters) + added})")
    
    # 4. Update monster count
    total = len(monsters) + added
    data[MONSTER_COUNT] = total
    print(f"\nMonster count: {total} (offset 0x{MONSTER_COUNT:04X})")
    
    # 5. Max the level byte at 0x101C
    data[LEVEL_BYTE] = 99
    data[LEVEL_BYTE_MIRROR] = 99
    print(f"Level byte: 99 (0x{LEVEL_BYTE:04X} + mirror 0x{LEVEL_BYTE_MIRROR:04X})")
    
    # 6. Max stats block at 0x10A0
    # Set all non-FF, non-00 values in the stats block to high values
    print("\nMaxing stats block 0x10A0-0x10C2...")
    for i in range(STATS_BLOCK, STATS_BLOCK + 0x23):
        if data[i] not in (0x00, 0xFF, 0xA1, 0xB1, 0xC1, 0x80, 0x81):
            # Don't touch structural bytes (markers, separators)
            if data[i] < 0x80:
                data[i] = 0x63  # 99 decimal
    
    # 7. Mirror the roster to the mirror region
    # Copy 0x4000 roster to mirror at 0x64A8
    roster_size = (len(monsters) + added) * RECORD_SIZE
    # Find the mirror base by matching pattern
    # From our diff: 0x4000 data appears at 0x64AB
    MIRROR_BASE = 0x64AB
    print(f"\nMirroring roster to 0x{MIRROR_BASE:04X}...")
    for i in range(roster_size + RECORD_SIZE):  # +1 record for FF terminator
        if MONSTER_ROSTER + i < len(data) and MIRROR_BASE + i < len(data):
            data[MIRROR_BASE + i] = data[MONSTER_ROSTER + i]
    
    # 8. Mirror stats block
    # 0x10A0 mirrors to ~0x6463
    for i in range(0x23):
        if STATS_BLOCK + i < len(data) and 0x6463 + i < len(data):
            data[0x6463 + i] = data[STATS_BLOCK + i]
    
    # Write
    write_save(save_path, data)
    print(f"\n✔ Saved! Reload in RetroArch (F1 → Reset)")
    print(f"  Backup at: {backup}")
    print(f"\n  Star Chips: 99")
    print(f"  Monsters: {total} (all Lv99, max stats)")
    print(f"  All IDs 1-80 added")

