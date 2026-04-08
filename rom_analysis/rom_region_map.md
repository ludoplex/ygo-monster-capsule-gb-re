# Yu-Gi-Oh! Monster Capsule GB — Complete ROM Region Map

  0x6060C: LD A,(0xA002)
  0x60610: LD A,(0xA003)
  0x60615: LD A,(0xA014)
  0x6061E: LD (0xA005),A
  0x60622: LD (0xA004),A
  0x60626: LD A,(0xA007)
  0x6062A: JR Z,0x60634
  0x6062F: JR Z,0x60634
  0x60634: LD A,(0xA004)
  0x60638: LD A,(0xA005)
    0x00506 (Bank 0): ID69:Lv5, ID56:Lv55, ID71:Lv79, ID62:Lv90
    0x015EA (Bank 0): ID147:Lv135, ID32:Lv5, ID35:Lv35, ID35:Lv35
    0x01BB7 (Bank 0): ID192:Lv42, ID18:Lv35, ID35:Lv35, ID19:Lv5
    0x01BD4 (Bank 0): ID192:Lv26, ID34:Lv35, ID35:Lv35, ID19:Lv5
    0x01DF6 (Bank 0): ID254:Lv29, ID15:Lv30, ID32:Lv30, ID49:Lv30
    0x01F22 (Bank 0): ID0:Lv25, ID17:Lv45, ID31:Lv213, ID42:Lv95
    0x02B8E (Bank 0): ID70:Lv10, ID68:Lv95, ID2:Lv205, ID70:Lv10
    0x030DD (Bank 0): ID61:Lv40, ID29:Lv61, ID40:Lv70, ID61:Lv40
    0x031D9 (Bank 0): ID70:Lv35, ID35:Lv78, ID35:Lv35, ID86:Lv35
    0x03C10 (Bank 0): ID46:Lv27, ID34:Lv60, ID34:Lv60, ID34:Lv60
    0x049E2 (Bank 1): ID194:Lv230, ID32:Lv40, ID3:Lv35, ID35:Lv35
    0x04C04 (Bank 1): ID12:Lv35, ID35:Lv5, ID32:Lv244, ID24:Lv35
    0x0503A (Bank 1): ID34:Lv35, ID35:Lv58, ID34:Lv35, ID35:Lv35
    0x05B5A (Bank 1): ID79:Lv45, ID76:Lv84, ID45:Lv15, ID99:Lv45
    0x05C87 (Bank 1): ID69:Lv55, ID94:Lv70, ID55:Lv238, ID70:Lv55
    0x08123: 03 0B D0 C3 29 41 01 01 01 01 01 01 01 01 01 01 01 01 01 01
    0x08138: 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01
    0x08762: 00 0D 0B 07 04 C3 00 68 5B 38 05 01 0F 07 03 0F 08 05 0F 09
    0x0878F: 00 09 0D 0B 04 C3 00 48 6B 58 06 01 0B 0C 03 0B 0D 05 0B 0E
    0x0931C: E7 E8 E9 EA 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01 01
  0x00000-0x03FFF  Bank  0: System routines, screen loader, sound driver
  0x04000-0x07FFF  Bank  1: Capsule drop logic, star chip mgmt, game state
  0x08000-0x0BFFF  Bank  2: World map/screen handling, floor data
    0x0B456: *** BASE STAT TABLE (112 × 8 bytes) ***
  0x0C000-0x0FFFF  Bank  3: Sound test, soundtrack loading
  0x10000-0x1FFFF  Banks 4-7: Dialogue text (floors 1-6?)
  0x20000-0x23FFF  Bank  8: Battle system code
    0x25317: Species data table (125 × 4 bytes, IDs 0-124)
  0x24000-0x27FFF  Bank  9: Battle support, data tables
  0x28000-0x2FFFF  Banks 10-11: Game logic, dialogue
  0x30000-0x37FFF  Banks 12-13: Data tables, map data
  0x38000-0x3BFFF  Bank 14: Monster names, skill names, pointer tables
  0x3C000-0x3FFFF  Bank 15: Dialogue text
  0x40000-0x4BFFF  Banks 16-18: Capsule machines, dialogue, sprite pointers
    0x48000: Capsule machine loot tables
  0x4C000-0x5FFFF  Banks 19-23: Mixed code/data/dialogue
  0x60000-0x63FFF  Bank 24: Save validation, title screen
  0x64000-0x77FFF  Banks 25-29: Dialogue, floor-specific data
  0x78000-0x7FFFF  Banks 30-31: Pure data tables
  0x80000-0x8BFFF  Banks 32-34: Dialogue text (heavy)
  0x8C000-0x8FFFF  Bank 35: EMPTY (unused ROM)
  0x90000-0x9FFFF  Banks 36-39: Code + graphics (sprites)
  0xA0000-0xABFFF  Banks 40-42: Dialogue text (heaviest region)
  0xAC000-0xBFFFF  Banks 43-47: Mixed data/dialogue
  0xC0000-0xDBFFF  Banks 48-54: Dialogue text (story content)
  0xDC000-0xE7FFF  Banks 55-57: Code + graphics
  0xE8000-0xFBFFF  Banks 58-62: Mixed code/data/text
  0xFC000-0xFFFFF  Bank 63: Misc code + empty
