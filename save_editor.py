#!/usr/bin/env python3
"""
Yu-Gi-Oh! Monster Capsule GB — Save Editor v3
Based on confirmed RE findings from dynamic analysis + Data Crystal.

Save format at SRAM offset 0x4000:
  14-byte records per monster:
    [0]  0x80 = owned marker
    [1]  Monster species ID (0x00-0x6F=monster, 0x77-0x7C=item)
    [2]  Level (1-99)
    [3]  EXP toward next level (wraps on level-up)
    [4]  HP (recomputed from base × level at battle load)
    [5]  0x00
    [6]  ATK
    [7]  DEF
    [8]  SPD
    [9]  0x00
    [10] Movement type (0x31=ground, 0x71=flying)
    [11] Species data byte
    [12-13] Species data (sprite/type refs)

Key save addresses:
  0x0204 = monster count
  0x6374 = star chips
  0x4000 = monster roster (primary)
  0x64AB = monster roster (mirror)
  0x101C = level tracking
  0x63E0 = level tracking (mirror)
"""

import sys
import shutil
import argparse
from pathlib import Path

# ─────────────────────────────────────────────
# Monster database — species-constant bytes from RE
# Format: id -> (movement_type, b11, b12, b13)
# ─────────────────────────────────────────────
SPECIES_DATA = {
    # Confirmed from save analysis
    0:  (0x31, 0x00, 0x5C, 0xFF),  # Ninja Squid
    2:  (0x31, 0x02, 0x5E, 0xFF),  # Jellyfish
    6:  (0x71, 0x06, 0x61, 0xA4),  # Great Pa
    7:  (0x31, 0x07, 0x62, 0xFF),  # Gumbo
    8:  (0x31, 0x08, 0x63, 0xFF),  # Torike
    11: (0x31, 0x0C, 0x66, 0xFF),  # Tiger Axe
    22: (0x71, 0x14, 0xC8, 0xCB),  # Toppo
    37: (0x71, 0x21, 0x79, 0xAA),  # DinosaurWing
    38: (0x71, 0x22, 0x7A, 0xAB),  # Armorsaurus
    54: (0x31, 0x32, 0xC8, 0xFF),  # Mogley
    55: (0x31, 0x33, 0xC8, 0xFF),  # Brain Slime
    57: (0x71, 0x35, 0x88, 0xCA),  # Eye Mouth
    60: (0x31, 0x38, 0x8B, 0xFF),  # Mushroom Man
    62: (0x31, 0x39, 0x8D, 0xFF),  # Big Insect
}

# Monster names (from ROM name table at 0x38000)
NAMES = {
    0:"Ninja Squid", 1:"Great White", 2:"Jellyfish", 3:"Fiend Kraken",
    4:"CatpltTurtle", 5:"Leviathan", 6:"Great Pa", 7:"Gumbo",
    8:"Torike", 9:"BeaverWarior", 10:"BattleWarior", 11:"Tiger Axe",
    12:"MysticHorsmn", 13:"Axe Raider", 14:"Battle Steer", 15:"Battleguard",
    16:"Garoozis", 17:"FlamSwordsmn", 18:"Battle Ox", 19:"RabidHorsemn",
    20:"GaiaFiercKni", 21:"GaiaDrgnChmp", 22:"Toppo", 23:"Torigun",
    24:"Mtn Warrior", 25:"RockOgreGrot", 26:"Ryu-Kishin", 27:"HitotsMeGian",
    28:"Harpie Lady", 29:"WingedDragon", 30:"BlacklndDrgn", 31:"Ryu-Kishin P",
    32:"CrawlingDrgn", 33:"KoumoriDragn", 34:"CurseOfDragn", 35:"Baby Dragon",
    36:"??? Dragon", 37:"DinosaurWing", 38:"Armorsaurus", 39:"ArmordLizard",
    40:"Uraby", 41:"SwdArmOfDrgn", 42:"Megazowler", 43:"TwoHeadKRex",
    44:"Head Sucker", 45:"SkullServant", 46:"TheSnakeHair", 47:"MamothGrvyrd",
    48:"Clown Zombie", 49:"ArmordZombie", 50:"DragonZombie", 51:"Pumpking",
    52:"Beeton", 53:"Hyper Beetle", 54:"Mogley", 55:"Brain Slime",
    56:"Flower Man", 57:"Eye Mouth", 58:"Big Foot", 59:"Kuriboh",
    60:"Mushroom Man", 61:"Cobrada", 62:"Big Insect", 63:"Basic Insect",
    64:"KillerNeedle", 65:"Gokibore", 66:"Wolf", 67:"Silver Fang",
    68:"Worm Beast", 69:"Larvae Moth", 70:"Great Moth #", 71:"Great Moth 1",
    72:"Great Moth 2", 73:"Great Moth 3", 74:"Great Moth 4", 75:"Dragon Piper",
    76:"SaggiDrkClwn", 77:"Horn Imp", 78:"Gremlin", 79:"Grappler",
    80:"Zanki", 81:"La Jinn", 82:"Crass Clown", 83:"Dungeon Worm",
    84:"Shadow Ghoul", 85:"Swordstalker", 86:"Barox", 87:"Dark Chimera",
    88:"Judge Man", 89:"MetlGuardian", 90:"FacelessMage", 91:"R.E.B.Dragon",
    92:"DarkMagician", 93:"SummondSkull", 94:"KngYamimakai", 95:"BlckSkulDrgn",
    96:"ExodiaLftArm", 97:"ExodiaRgtArm", 98:"Exodias Legs", 99:"Exodias Body",
    100:"Exodia", 101:"Mystical Elf", 102:"Rogue Doll", 103:"CeltcGuardin",
    104:"Wattkid", 105:"DrgCapturJar", 106:"B.E.W.Dragon", 107:"B.E.U.Dragon",
    108:"ToonAligator", 109:"ParrotDragon", 110:"Dark Rabbit", 111:"Rude Kaiser",
    119:"Evo Capsule", 120:"SkillCapsule", 121:"HP Capsule",
    122:"AT Capsule", 123:"DF Capsule", 124:"SP Capsule",
}

# Type categories for movement type estimation
FLYING_IDS = {6, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 37, 38, 57, 69,
              70, 71, 72, 73, 74, 75, 101, 105, 106, 107}

RECORD_SIZE = 14
ROSTER_START = 0x4000
ROSTER_MIRROR = 0x64AB
MAX_ROSTER_END = 0x4800  # Safety limit


def get_species_bytes(mid):
    """Get species-constant bytes for a monster ID."""
    if mid in SPECIES_DATA:
        return SPECIES_DATA[mid]
    # Estimate for unknown monsters
    mv = 0x71 if mid in FLYING_IDS else 0x31
    # b11 pattern: roughly tracks ID but with offsets for higher IDs
    if mid <= 10:
        b11 = mid
    elif mid <= 23:
        b11 = mid - 2
    else:
        b11 = mid - 4
    b11 = max(0, min(0x7F, b11))
    b12 = 0x63 if mv == 0x31 else 0xC8
    b13 = 0xFF if mv == 0x31 else 0xCB
    return (mv, b11, b12, b13)


def make_record(mid, level=99, exp=0, hp=99, atk=99, def_=99, spd=99):
    """Create a 14-byte monster record."""
    mv, b11, b12, b13 = get_species_bytes(mid)
    return bytes([
        0x80, mid, level, exp,
        hp, 0x00, atk, def_, spd, 0x00,
        mv, b11, b12, b13
    ])


def parse_roster(data, base=ROSTER_START):
    """Parse all monster records from save data."""
    monsters = []
    i = base
    while i < base + 0x800:
        if data[i] == 0x80 and i + 1 < len(data) and data[i+1] != 0xFF:
            rec = data[i:i+RECORD_SIZE]
            if len(rec) < RECORD_SIZE:
                break
            monsters.append({
                'offset': i,
                'id': rec[1],
                'name': NAMES.get(rec[1], f"ID{rec[1]}"),
                'level': rec[2],
                'exp': rec[3],
                'hp': rec[4],
                'atk': rec[6],
                'def': rec[7],
                'spd': rec[8],
                'move': rec[10],
                'raw': rec,
            })
            i += RECORD_SIZE
        elif data[i] == 0xFF:
            break
        else:
            i += 1
    return monsters


def cmd_list(args):
    """List current roster."""
    data = open(args.save, 'rb').read()
    monsters = parse_roster(bytearray(data))
    chips = data[0x6374]
    count = data[0x0204]
    
    print(f"Save: {args.save}")
    print(f"Star Chips: {chips}  |  Monster Count: {count}")
    print(f"{'#':>3} {'Name':>14} {'Lv':>3} {'EXP':>4} {'HP':>3} {'ATK':>4} {'DEF':>4} {'SPD':>4} {'Mv':>5}")
    print("─" * 48)
    for i, m in enumerate(monsters):
        mv = "Grnd" if m['move'] == 0x31 else "Fly" if m['move'] == 0x71 else f"{m['move']:02X}"
        print(f"{i+1:3d} {m['name']:>14} {m['level']:3d} {m['exp']:4d} {m['hp']:3d} {m['atk']:4d} {m['def']:4d} {m['spd']:4d} {mv:>5}")
    print(f"\nTotal: {len(monsters)} monsters")


def cmd_max(args):
    """Max out all existing monsters' levels and stats."""
    data = bytearray(open(args.save, 'rb').read())
    shutil.copy2(args.save, args.save + '.bak')
    
    monsters = parse_roster(data)
    for m in monsters:
        off = m['offset']
        data[off + 2] = args.level  # Level
        # Stats will be recomputed by game engine at battle load
        # but set them high so they display correctly in menus
        data[off + 4] = min(99, args.level + 20)  # HP scales with level
        data[off + 6] = min(99, args.level // 5 + 5)  # ATK
        data[off + 7] = min(99, args.level // 5 + 5)  # DEF
        data[off + 8] = min(99, args.level // 5 + 5)  # SPD
        print(f"  {m['name']:>14}: Lv{m['level']} → Lv{args.level}")
    
    # Mirror
    roster_len = len(monsters) * RECORD_SIZE + 1
    for i in range(roster_len):
        if ROSTER_START + i < len(data) and ROSTER_MIRROR + i < len(data):
            data[ROSTER_MIRROR + i] = data[ROSTER_START + i]
    
    data[0x101C] = args.level
    data[0x63E0] = args.level
    
    open(args.save, 'wb').write(data)
    print(f"\n✔ {len(monsters)} monsters maxed to Lv{args.level}")
    print(f"  Backup: {args.save}.bak")


def cmd_chips(args):
    """Set star chips."""
    data = bytearray(open(args.save, 'rb').read())
    shutil.copy2(args.save, args.save + '.bak')
    data[0x6374] = args.amount
    open(args.save, 'wb').write(data)
    print(f"✔ Star Chips set to {args.amount}")


def cmd_unlock_all(args):
    """Add all monsters to roster at specified level."""
    data = bytearray(open(args.save, 'rb').read())
    shutil.copy2(args.save, args.save + '.bak')
    
    existing = parse_roster(data)
    existing_ids = {m['id'] for m in existing}
    
    # Find next available slot
    if existing:
        next_pos = max(m['offset'] for m in existing) + RECORD_SIZE
    else:
        next_pos = ROSTER_START
    
    added = 0
    # Add all 112 monsters (IDs 0-111)
    for mid in range(112):
        if mid not in existing_ids and next_pos + RECORD_SIZE < MAX_ROSTER_END:
            rec = make_record(mid, level=args.level)
            data[next_pos:next_pos+RECORD_SIZE] = rec
            next_pos += RECORD_SIZE
            added += 1
    
    # Add items if requested
    if args.items:
        for mid in range(119, 125):
            if mid not in existing_ids and next_pos + RECORD_SIZE < MAX_ROSTER_END:
                rec = make_record(mid, level=99, hp=0, atk=0, def_=0, spd=0)
                data[next_pos:next_pos+RECORD_SIZE] = rec
                next_pos += RECORD_SIZE
                added += 1
    
    # Terminate
    data[next_pos] = 0xFF
    
    # Update count
    total = len(existing) + added
    data[0x0204] = total
    
    # Max star chips
    data[0x6374] = 99
    
    # Max existing monsters too
    for m in existing:
        off = m['offset']
        data[off + 2] = args.level
    
    # Level tracking
    data[0x101C] = args.level
    data[0x63E0] = args.level
    
    # Mirror roster
    roster_len = next_pos - ROSTER_START + 1
    for i in range(roster_len):
        if ROSTER_START + i < len(data) and ROSTER_MIRROR + i < len(data):
            data[ROSTER_MIRROR + i] = data[ROSTER_START + i]
    
    open(args.save, 'wb').write(data)
    print(f"✔ Added {added} new monsters (total: {total})")
    print(f"  All at Lv{args.level}, 99 star chips")
    print(f"  Backup: {args.save}.bak")


def cmd_pvp(args):
    """Create a fair PvP save — all monsters, equal level, no EXP advantage."""
    data = bytearray(open(args.save, 'rb').read())
    shutil.copy2(args.save, args.save + '.bak')
    
    pos = ROSTER_START
    count = 0
    
    # Write every monster at the same level with zero EXP
    for mid in range(112):
        rec = make_record(mid, level=args.level, exp=0)
        data[pos:pos+RECORD_SIZE] = rec
        pos += RECORD_SIZE
        count += 1
    
    # Add all items
    for mid in range(119, 125):
        rec = make_record(mid, level=99, exp=99, hp=0, atk=0, def_=0, spd=0)
        data[pos:pos+RECORD_SIZE] = rec
        pos += RECORD_SIZE
        count += 1
    
    # Terminate
    data[pos] = 0xFF
    
    # Update metadata
    data[0x0204] = count
    data[0x6374] = 99  # Star chips
    data[0x101C] = args.level
    data[0x63E0] = args.level
    
    # Mirror
    roster_len = pos - ROSTER_START + 1
    for i in range(roster_len):
        if ROSTER_START + i < len(data) and ROSTER_MIRROR + i < len(data):
            data[ROSTER_MIRROR + i] = data[ROSTER_START + i]
    
    open(args.save, 'wb').write(data)
    print(f"✔ PvP save created!")
    print(f"  {count} entries (112 monsters + 6 items)")
    print(f"  All monsters at Lv{args.level} with 0 EXP (equal footing)")
    print(f"  99 star chips")
    print(f"  Stats will be recomputed by game engine at battle load")
    print(f"\n  Copy this save to both players for fair matches.")
    print(f"  Backup: {args.save}.bak")


def main():
    parser = argparse.ArgumentParser(
        description="Yu-Gi-Oh! Monster Capsule GB — Save Editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list game.sav                    Show current roster
  %(prog)s max game.sav                     Max all monster levels to 99
  %(prog)s max game.sav --level 50          Max to level 50
  %(prog)s chips game.sav 99                Set star chips to 99
  %(prog)s unlock game.sav                  Add all 112 monsters at Lv99
  %(prog)s unlock game.sav --level 50       Add all monsters at Lv50
  %(prog)s pvp game.sav                     Create fair PvP save (all Lv50)
  %(prog)s pvp game.sav --level 99          Create PvP save at Lv99
        """)
    
    sub = parser.add_subparsers(dest='command')
    
    # list
    p = sub.add_parser('list', help='List current roster')
    p.add_argument('save', help='Save file path (.sav/.srm)')
    
    # max
    p = sub.add_parser('max', help='Max all existing monsters')
    p.add_argument('save', help='Save file path')
    p.add_argument('--level', type=int, default=99, help='Target level (default: 99)')
    
    # chips
    p = sub.add_parser('chips', help='Set star chips')
    p.add_argument('save', help='Save file path')
    p.add_argument('amount', type=int, help='Star chip amount (0-99)')
    
    # unlock
    p = sub.add_parser('unlock', help='Add all monsters to roster')
    p.add_argument('save', help='Save file path')
    p.add_argument('--level', type=int, default=99, help='Level for new monsters')
    p.add_argument('--items', action='store_true', default=True, help='Include capsule items')
    
    # pvp
    p = sub.add_parser('pvp', help='Create fair PvP save')
    p.add_argument('save', help='Save file path')
    p.add_argument('--level', type=int, default=50, help='Level for all monsters (default: 50)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    {'list': cmd_list, 'max': cmd_max, 'chips': cmd_chips,
     'unlock': cmd_unlock_all, 'pvp': cmd_pvp}[args.command](args)


if __name__ == '__main__':
    main()
