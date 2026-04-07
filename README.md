# Yu-Gi-Oh! Monster Capsule GB — Reverse Engineering

Reverse engineering research for Yu-Gi-Oh! Monster Capsule GB (Game Boy, Konami 2000).

Conducted as part of the Computer Store LAN Center curriculum in Wheatland, WY — teaching binary analysis, save file hacking, and game reverse engineering.

## Findings

### Save File Format (`0x4000` roster)

14-byte records per monster:

| Byte | Field | Notes |
|------|-------|-------|
| 0 | Marker | `0x80`=save, `0xC0`=player battle, `0x60`=NPC |
| 1 | Monster ID | 0-111 monsters, 119-123 items |
| 2 | Level | 1-99 |
| 3 | EXP | Toward next level, wraps on level-up |
| 4 | HP | Recomputed from base × level at battle load |
| 5 | (zero) | |
| 6 | ATK | |
| 7 | DEF | |
| 8 | SPD | |
| 9 | (zero) | |
| 10 | Movement | `0x31`=ground, `0x71`=flying |
| 11-13 | Species data | Sprite/type references |

### Key Memory Addresses

| Address | Description |
|---------|-------------|
| `$C200` | Screen/mode (01=overworld, 05=battle, 07=attack) |
| `$C2ED` | Star Chips |
| `$C418` | Animation counter |
| `$C69A` | 6×6 battle grid (36 bytes) |
| `$C7E5` | Hit probability (88=88%) |
| `$C75D` | Dice roll (animated) |
| `$C75B` | Attack target ID |
| `$C763` | Damage total |
| `$C769` | Assist/space bonus |
| `$C850+` | Active monster records during battle |
| `$6374` | Star Chips (SRAM/save) |
| `$4000+` | Monster roster (SRAM/save) |

### Battle System

- **6×6 tactical grid** — chess-like movement
- **4v4** monster battles
- **Turn system** — pick one monster per turn: move-then-attack or attack-without-moving
- **Two dice roll** — determines attack power
- **Space type bonus** — terrain tiles affect combat
- **Assist bonus** — adjacent friendly monsters boost attack
- **EV-like stat growth** — stat gains on level-up influenced by battle history

### Capsule Machines

- **13 machines** with different loot pools decoded from ROM at `0x48000+`
- **Frame-based RNG** — result depends on exact frame you press A on "Yes"
- **Rewind + re-roll** works to get specific monsters

### Text Encoding

| Range | Characters |
|-------|-----------|
| `0x00-0x19` | a-z (lowercase) |
| `0x64-0x7D` | A-Z (uppercase) |
| `0x97` | space |
| `0x8B` | hyphen |
| `0xFF` | terminator |

Monster names at ROM `0x38000`, pointer table at `0x385A7` (124 entries).

### Monster Roster

112 monsters + 7 characters + 5 capsule items = 124 total entries.

See `monsters_complete.csv` for the full list with categories.

## Files

| File | Description |
|------|-------------|
| `monsters_complete.csv` | All 124 game entries with categories |
| `capsule_machines.csv` | 13 machine loot pools from ROM |
| `capsule_items.csv` | 5 capsule items |
| `my_roster.csv` | Example player roster |
| `memory_map.csv` | WRAM/SRAM address map |
| `record_format.csv` | 14-byte record structure |
| `battle_system.csv` | Battle mechanics documentation |
| `text_encoding.csv` | Character encoding table |
| `ygo_mcgb.sym` | mGBA symbol file for debugging |
| `save_editor.py` | Save file editor (level/roster) |
| `scripts/` | Lua scripts for mGBA dynamic analysis |

## Tools Used

- **mGBA 0.10.2** — emulation + Lua scripting + debugger
- **GHex** — hex editor for save/ROM analysis
- **Python** — IPS patching, binary diffing, save editing
- **Claude Code** — AI-assisted reverse engineering

## Credits

- Game: Konami (2000)
- English translation patch: [Bownly](https://github.com/Bownly/YGOMC)
- RE research: Vincent Anderson / MHI Computer Store
