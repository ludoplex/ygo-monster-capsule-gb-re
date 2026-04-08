# Yu-Gi-Oh! Monster Capsule GB — Reverse Engineering

Complete reverse engineering documentation for Yu-Gi-Oh! Monster Capsule GB
(Game Boy Color, Konami 2000). **The most comprehensive public documentation of this game.**

Conducted at the Computer Store LAN Center in Wheatland, WY — teaching binary analysis,
save file hacking, and game reverse engineering as part of MHI's workforce development curriculum.

## Key Discoveries

### Base Stat Table (ROM `0x0B456`)
8 bytes per monster, 112 entries:
```
B0 = HP Base     B1 = HP Max Growth per Level
B2 = ATK Base    B3 = ATK Max Growth per Level
B4 = DEF Base    B5 = DEF Max Growth per Level
B6 = SPD Base    B7 = SPD Max Growth per Level
```

### Growth Formula (Confirmed)
```
stat_gain_per_level = random(1, max_growth_rate)
stat_at_level_L = base + sum(random(1, growth) for each level 2..L)
```
This creates Pokemon-style stat variance between identical monsters.

### Save Record Format (`SRAM 0x4000+`)
14 bytes per monster:

| Byte | Field | Notes |
|------|-------|-------|
| 0 | Marker | `0x80`=save, `0xC0`=player battle, `0x60`=NPC |
| 1 | Monster ID | 0-111 monsters, 119-123 items |
| 2 | Level | 1-99 |
| 3 | EXP | Toward next level, wraps on level-up |
| 4 | HP | Recomputed from base x level at battle load |
| 5 | (zero) | |
| 6 | ATK | |
| 7 | DEF | |
| 8 | SPD | |
| 9 | (zero) | |
| 10 | Movement | `0x31`=Ground, `0x71`=Flying, `0x11`=Special |
| 11-13 | Species data | Sprite/type references from ROM `0x25317` |

### Battle System
- **6x6 tactical grid** — chess-like movement
- **4v4** monster battles
- **Turn**: pick one monster — move then attack, or attack without moving
- **Two dice roll** determines attack power
- **Space type bonus** from terrain tiles
- **Assist bonus** from adjacent friendly monsters
- **Hit probability** at WRAM `$C7E5` (88% standard)

### Capsule Machines
- 13 machines with different loot pools (ROM `0x48000+`)
- Frame-based RNG — result depends on exact frame you press A
- Rewind + re-roll works for specific monsters

### ROM Classification
- **92% classified** across 1 MiB ROM
- 60% text/dialogue, 15% empty, 14% code, 2% graphics, <1% data tables
- 230 skill names, 124 monster/item names, 13 capsule machines
- 112 monsters with full stat data + growth rates

## Files

| File | Description |
|------|-------------|
| `monster_database.csv` | **Complete** 26-field reference for all 112 monsters |
| `base_stat_table.csv` | Raw stat data from ROM (HP/ATK/DEF/SPD + growth rates) |
| `stat_ranges.csv` | Min/max/avg stats at Lv50 and Lv99 for all monsters |
| `species_data_table.csv` | Movement type + sprite data from ROM |
| `species_data.py` | Python dict for programmatic access |
| `monsters_complete.csv` | All 124 game entries with categories |
| `capsule_machines.csv` | 13 capsule machine loot pools decoded from ROM |
| `skill_names.csv` | 230 attack/skill names from ROM |
| `capsule_items.csv` | 5 capsule items (Evo, Skill, HP, AT, DF) |
| `memory_map.csv` | 40+ WRAM/SRAM addresses with descriptions |
| `record_format.csv` | 14-byte save record structure |
| `battle_system.csv` | Battle mechanics documentation |
| `text_encoding.csv` | Character encoding table (a=0x00, A=0x64) |
| `save_editor.py` | CLI save editor (list/max/chips/unlock/pvp) |
| `scripts/*.lua` | 6 mGBA Lua scripts for dynamic analysis |
| `ygo_mcgb.sym` | mGBA symbol file for debugging |
| `rom_analysis/` | Bank analysis, visual ROM map, 14 session notes |

## Save Editor
```bash
python3 save_editor.py list game.sav          # View roster
python3 save_editor.py max game.sav           # Max all levels to 99
python3 save_editor.py chips game.sav 99      # Set star chips
python3 save_editor.py unlock game.sav        # Add all 112 monsters
python3 save_editor.py pvp game.sav --level 50  # Fair PvP save
```

## Tools Used
- **mGBA 0.10.2** — emulation + Lua scripting + debugger
- **GHex** — hex editor for save/ROM analysis
- **Python** — IPS patching, binary diffing, save editing, ROM analysis
- **Claude Code** — AI-assisted reverse engineering (14 autonomous sessions)

## Credits
- Game: Konami (2000)
- English translation: [Bownly](https://github.com/Bownly/YGOMC)
- RE research: Vincent Anderson / MHI Computer Store
- Data Crystal wiki contributors for initial ROM/RAM map seeds