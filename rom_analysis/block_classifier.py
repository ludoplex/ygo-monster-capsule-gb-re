#!/usr/bin/env python3
"""
Professional GBC ROM Block Classifier
======================================
Multi-signal static analysis for Yu-Gi-Oh! Monster Capsule GB.

Classification methodology:
  1. Z80/GB opcode validity & frequency analysis
  2. Shannon entropy measurement
  3. Game-specific text encoding detection
  4. 2bpp tile graphics pattern recognition
  5. Pointer table detection (little-endian 16-bit addresses)
  6. Repetition/padding detection
  7. Data table structure detection (fixed-stride records)

Each block gets a confidence-weighted score for each category.
The highest-confidence category wins, with a minimum threshold.
"""

import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

# ─── Game-specific constants ───────────────────────────────────────────

# Custom text encoding: a=0x00..z=0x19, A=0x64..Z=0x7D,
# 0=0x50..9=0x59, space=0x1A, punctuation in 0x1B-0x4F range,
# newline/terminator around 0x80-0x8F, dakuten/handakuten marks
TEXT_RANGES = [
    (0x00, 0x19),  # a-z
    (0x1A, 0x1A),  # space
    (0x1B, 0x4F),  # punctuation, kana, special chars
    (0x50, 0x59),  # 0-9
    (0x5A, 0x63),  # more punctuation/special
    (0x64, 0x7D),  # A-Z
    (0x80, 0x8F),  # control codes (newline, terminator, etc.)
    (0xFE, 0xFF),  # string terminators
]

def is_text_byte(b):
    """Check if byte falls in the game's text encoding ranges."""
    for lo, hi in TEXT_RANGES:
        if lo <= b <= hi:
            return True
    return False

# GB Z80 single-byte opcodes that are VALID on the Game Boy CPU
# These are the most common opcodes in real GB code
COMMON_GB_OPCODES = {
    0x00,  # NOP
    0x01, 0x11, 0x21, 0x31,  # LD rr,nn (16-bit immediate loads)
    0x02, 0x12, 0x22, 0x32,  # LD (rr),A variants
    0x03, 0x13, 0x23, 0x33,  # INC rr
    0x04, 0x05, 0x0C, 0x0D, 0x14, 0x15, 0x1C, 0x1D,  # INC/DEC r
    0x24, 0x25, 0x2C, 0x2D, 0x34, 0x35, 0x3C, 0x3D,
    0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,  # LD r,n
    0x0A, 0x1A, 0x2A, 0x3A,  # LD A,(rr) variants
    0x0B, 0x1B, 0x2B, 0x3B,  # DEC rr
    0x18, 0x20, 0x28, 0x30, 0x38,  # JR cc,e
    0x76,  # HALT
    0xC0, 0xC8, 0xC9, 0xD0, 0xD8, 0xD9,  # RET variants
    0xC1, 0xD1, 0xE1, 0xF1,  # POP rr
    0xC3, 0xC2, 0xCA, 0xD2, 0xDA,  # JP variants
    0xC5, 0xD5, 0xE5, 0xF5,  # PUSH rr
    0xCD, 0xC4, 0xCC, 0xD4, 0xDC,  # CALL variants
    0xE0, 0xF0,  # LDH (n),A / LDH A,(n) — very common in GB
    0xE2, 0xF2,  # LD (C),A / LD A,(C)
    0xEA, 0xFA,  # LD (nn),A / LD A,(nn)
    0xE6, 0xEE, 0xF6, 0xFE,  # AND/XOR/OR/CP n
    0xCB,  # CB prefix (bit operations — extremely common in GB)
    0xAF,  # XOR A (common register clear)
    0xC6, 0xCE, 0xD6, 0xDE,  # ADD/ADC/SUB/SBC A,n
    0xE9,  # JP (HL)
    0xF3, 0xFB,  # DI/EI
    0xF8, 0xF9,  # LD HL,SP+e / LD SP,HL
}

# LD r,r' opcodes: 0x40-0x7F minus 0x76 (HALT) — register-to-register moves
for i in range(0x40, 0x80):
    if i != 0x76:
        COMMON_GB_OPCODES.add(i)

# ALU A,r opcodes: 0x80-0xBF — ADD/ADC/SUB/SBC/AND/XOR/OR/CP with register
for i in range(0x80, 0xC0):
    COMMON_GB_OPCODES.add(i)

# Opcodes that are INVALID on Game Boy (exist on Z80 but removed from GB CPU)
INVALID_GB_OPCODES = {
    0x08,  # Actually valid on GB (LD (nn),SP) but rare
    0xD3, 0xDB, 0xDD, 0xE3, 0xE4, 0xEB, 0xEC, 0xED, 0xF4, 0xFC, 0xFD,
}
# Note: 0x10 (STOP) and 0x08 (LD (nn),SP) ARE valid on GB, just uncommon

# RST vectors — very common as CALL shortcuts in GB code
RST_OPCODES = {0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF}
COMMON_GB_OPCODES.update(RST_OPCODES)


# ─── Analysis functions ────────────────────────────────────────────────

def shannon_entropy(data: bytes) -> float:
    """Calculate Shannon entropy in bits per byte (0.0 - 8.0)."""
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def text_score(data: bytes) -> float:
    """Score how likely this block is text (0.0 - 1.0)."""
    if not data:
        return 0.0
    text_bytes = sum(1 for b in data if is_text_byte(b))
    ratio = text_bytes / len(data)

    # Bonus: check for string terminators (0xFF or 0x80) appearing periodically
    terminators = sum(1 for b in data if b in (0xFF, 0x80, 0x81, 0xFE))
    term_ratio = terminators / len(data)

    # Text blocks typically have 70%+ text bytes with scattered terminators
    if ratio > 0.7 and 0.01 < term_ratio < 0.15:
        return min(1.0, ratio + 0.1)
    return ratio


def code_score(data: bytes) -> float:
    """Score how likely this block is Z80/GB machine code (0.0 - 1.0)."""
    if not data:
        return 0.0

    valid_ops = 0
    invalid_ops = 0
    i = 0
    instructions = 0

    while i < len(data):
        op = data[i]
        instructions += 1

        if op in INVALID_GB_OPCODES:
            invalid_ops += 1
            i += 1
        elif op in COMMON_GB_OPCODES:
            valid_ops += 1
            # Skip operand bytes for multi-byte instructions
            if op in (0x01, 0x11, 0x21, 0x31, 0xC3, 0xC2, 0xCA, 0xD2, 0xDA,
                      0xCD, 0xC4, 0xCC, 0xD4, 0xDC, 0xEA, 0xFA):
                i += 3  # 3-byte instruction
            elif op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,
                        0x18, 0x20, 0x28, 0x30, 0x38, 0xE0, 0xF0,
                        0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE,
                        0xF8, 0xCB):
                i += 2  # 2-byte instruction
            else:
                i += 1  # 1-byte instruction
        else:
            i += 1

    if instructions == 0:
        return 0.0

    validity_ratio = valid_ops / instructions
    invalidity_penalty = invalid_ops / instructions

    # Strong code signal: high valid ratio, low invalid ratio
    score = validity_ratio - (invalidity_penalty * 3)

    # Bonus: check for common code patterns
    # RET (0xC9) appearing suggests function boundaries
    ret_count = data.count(0xC9)
    if 1 <= ret_count <= 30:
        score += 0.05

    # CALL (0xCD) appearing suggests structured code
    call_count = data.count(0xCD)
    if 1 <= call_count <= 40:
        score += 0.05

    # JR (relative jumps) are very common in tight GB code
    jr_count = sum(1 for b in data if b in (0x18, 0x20, 0x28, 0x30, 0x38))
    if jr_count >= 3:
        score += 0.05

    return max(0.0, min(1.0, score))


def graphics_score(data: bytes) -> float:
    """Score how likely this block is 2bpp tile graphics (0.0 - 1.0)."""
    if len(data) < 16:
        return 0.0

    # 2bpp tiles: 8x8 pixels, 2 bytes per row, 16 bytes per tile
    # Each pair of bytes represents one pixel row (low bit plane, high bit plane)
    # Graphics tend to have: byte pairs where both bytes have similar bit patterns,
    # runs of 0x00 (transparent), and moderate entropy

    signals = 0.0
    checks = 0

    # Check tile alignment: look at 16-byte chunks
    for tile_start in range(0, len(data) - 15, 16):
        tile = data[tile_start:tile_start + 16]
        checks += 1

        # In 2bpp, adjacent byte pairs form pixel rows
        # Common pattern: both bytes of a pair are similar or one is 0
        pair_similarity = 0
        zero_pairs = 0
        for row in range(8):
            b0 = tile[row * 2]
            b1 = tile[row * 2 + 1]
            if b0 == 0 and b1 == 0:
                zero_pairs += 1
            # Bits often overlap between planes
            if bin(b0 & b1).count('1') >= bin(b0 | b1).count('1') * 0.3:
                pair_similarity += 1

        # Graphics tiles often have some zero rows but not all
        if 1 <= zero_pairs <= 6:
            signals += 0.3
        if pair_similarity >= 4:
            signals += 0.3

    if checks == 0:
        return 0.0

    base_score = signals / checks

    # Entropy check: graphics typically 2.0-6.0 bits
    ent = shannon_entropy(data)
    if 2.0 <= ent <= 6.0:
        base_score += 0.1

    # Unique byte count: graphics tend to have moderate variety
    unique = len(set(data))
    if 10 <= unique <= 100:
        base_score += 0.1

    return min(1.0, base_score)


def data_table_score(data: bytes) -> float:
    """Score how likely this block is structured data tables (0.0 - 1.0)."""
    if len(data) < 8:
        return 0.0

    signals = 0.0

    # Check for repeating stride patterns (fixed-size records)
    for stride in (2, 4, 6, 8, 10, 12, 14, 16, 20):
        if len(data) < stride * 3:
            continue
        # Check if bytes at regular intervals have similar properties
        matches = 0
        total = 0
        for offset in range(stride):
            values = [data[offset + i * stride]
                      for i in range(min(10, len(data) // stride))]
            total += 1
            # Check if this column has constrained value range
            value_range = max(values) - min(values) if values else 256
            if value_range < 128:  # Column values are in a limited range
                matches += 1
        if total > 0 and matches / total > 0.6:
            signals = max(signals, 0.5 + (matches / total) * 0.3)

    # Check for pointer tables: sequences of 16-bit LE values
    # that look like ROM addresses (0x4000-0x7FFF for banked, 0x0000-0x3FFF for bank 0)
    ptr_count = 0
    for i in range(0, len(data) - 1, 2):
        val = struct.unpack_from('<H', data, i)[0]
        if 0x4000 <= val <= 0x7FFF or 0x0000 <= val <= 0x3FFF:
            ptr_count += 1
    ptr_ratio = ptr_count / (len(data) // 2) if len(data) >= 2 else 0
    if ptr_ratio > 0.5:
        signals = max(signals, 0.4 + ptr_ratio * 0.4)

    return min(1.0, signals)


def empty_score(data: bytes) -> float:
    """Score how likely this block is empty/padding (0.0 - 1.0)."""
    if not data:
        return 1.0

    # Count most common byte
    counts = Counter(data)
    most_common_byte, most_common_count = counts.most_common(1)[0]
    ratio = most_common_count / len(data)

    # Common padding bytes: 0x00, 0xFF, 0x01
    if most_common_byte in (0x00, 0xFF, 0x01) and ratio > 0.9:
        return ratio

    # Less common but valid: any single repeated byte > 95%
    if ratio > 0.95:
        return ratio * 0.9

    # Two-byte pattern filling (like 0x00 0x01 repeating)
    if len(data) >= 4:
        pair_counts = Counter()
        for i in range(0, len(data) - 1, 2):
            pair_counts[(data[i], data[i+1])] += 1
        if pair_counts:
            top_pair_count = pair_counts.most_common(1)[0][1]
            pair_ratio = top_pair_count / (len(data) // 2)
            if pair_ratio > 0.8:
                return pair_ratio * 0.85

    return 0.0


def classify_block(data: bytes, block_index: int, bank: int) -> dict:
    """
    Classify a 256-byte ROM block using all analysis methods.
    Returns dict with category, confidence, and sub-scores.
    """
    scores = {
        'text': text_score(data),
        'code': code_score(data),
        'graphics': graphics_score(data),
        'data': data_table_score(data),
        'empty': empty_score(data),
    }

    entropy = shannon_entropy(data)
    unique_bytes = len(set(data))

    # Apply entropy-based adjustments
    if entropy < 1.0:
        scores['empty'] = max(scores['empty'], 0.7)
        scores['code'] *= 0.3
        scores['text'] *= 0.3
    elif entropy < 3.0:
        # Low entropy: likely text or simple data
        scores['graphics'] *= 0.5
    elif entropy > 7.0:
        # Very high entropy: likely compressed or encrypted
        scores['text'] *= 0.3
        scores['empty'] *= 0.1

    # Apply unique byte count adjustments
    if unique_bytes <= 3:
        scores['empty'] = max(scores['empty'], 0.8)

    # Determine winner
    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]

    # If confidence is too low, use secondary heuristics
    if best_score < 0.3:
        # Fallback: entropy-based classification
        if entropy < 1.5:
            best_cat = 'empty'
            best_score = 0.4
        elif entropy < 4.5:
            best_cat = 'text'
            best_score = 0.35
        elif entropy < 6.0:
            best_cat = 'code'
            best_score = 0.35
        else:
            best_cat = 'data'
            best_score = 0.3

    # Sub-classification for data blocks
    sub_type = None
    if best_cat == 'data':
        # Check if it's a pointer table
        ptr_count = 0
        for i in range(0, len(data) - 1, 2):
            val = struct.unpack_from('<H', data, i)[0]
            if 0x4000 <= val <= 0x7FFF:
                ptr_count += 1
        if ptr_count > len(data) // 4:
            sub_type = 'pointer_table'
        else:
            sub_type = 'structured_data'
    elif best_cat == 'code':
        # Check if it's mostly a jump/dispatch table
        jp_count = sum(1 for i in range(0, len(data) - 2, 3)
                       if data[i] in (0xC3, 0xCD))
        if jp_count > 20:
            sub_type = 'dispatch_table'
        else:
            sub_type = 'executable'
    elif best_cat == 'text':
        # Check for dialogue vs menu/item names
        term_spacing = []
        last_term = -1
        for i, b in enumerate(data):
            if b in (0xFF, 0x80, 0xFE):
                if last_term >= 0:
                    term_spacing.append(i - last_term)
                last_term = i
        if term_spacing:
            avg_spacing = sum(term_spacing) / len(term_spacing)
            if avg_spacing < 20:
                sub_type = 'names_list'
            else:
                sub_type = 'dialogue'
        else:
            sub_type = 'dialogue'
    elif best_cat == 'graphics':
        sub_type = '2bpp_tiles'
    elif best_cat == 'empty':
        counts = Counter(data)
        fill_byte = counts.most_common(1)[0][0]
        sub_type = f'padding_0x{fill_byte:02X}'

    return {
        'category': best_cat,
        'sub_type': sub_type,
        'confidence': round(best_score, 3),
        'entropy': round(entropy, 3),
        'unique_bytes': unique_bytes,
        'scores': {k: round(v, 3) for k, v in scores.items()},
        'block_index': block_index,
        'offset': f'0x{block_index * 256:05X}',
        'bank': bank,
    }


def classify_rom(rom_path: str, block_map_path: str) -> list[dict]:
    """Classify all mixed blocks in the ROM."""
    rom = Path(rom_path).read_bytes()

    with open(block_map_path) as f:
        block_map = json.load(f)

    blocks = block_map['blocks']
    results = []

    for i, cat in enumerate(blocks):
        if cat == 'mixed':
            offset = i * 256
            bank = i // 64  # 16KB banks = 64 blocks
            data = rom[offset:offset + 256]
            result = classify_block(data, i, bank)
            results.append(result)

    return results


def update_block_map(block_map_path: str, classifications: list[dict]) -> dict:
    """Update block_map.json with new classifications."""
    with open(block_map_path) as f:
        block_map = json.load(f)

    for cls in classifications:
        idx = cls['block_index']
        block_map['blocks'][idx] = cls['category']

    # Recount categories
    from collections import Counter
    cats = Counter(block_map['blocks'])
    block_map['categories'] = dict(sorted(cats.items(), key=lambda x: -x[1]))

    return block_map


def generate_report(classifications: list[dict]) -> str:
    """Generate a detailed markdown report of classifications."""
    lines = []
    lines.append("# Mixed Block Reclassification Report\n")
    lines.append(f"**Total blocks reclassified:** {len(classifications)}\n")

    # Summary by new category
    from collections import Counter
    new_cats = Counter(c['category'] for c in classifications)
    lines.append("## Summary\n")
    lines.append("| Category | Count | % of reclassified |")
    lines.append("|----------|-------|-------------------|")
    for cat, count in sorted(new_cats.items(), key=lambda x: -x[1]):
        pct = count / len(classifications) * 100
        lines.append(f"| {cat} | {count} | {pct:.1f}% |")

    # Confidence distribution
    lines.append("\n## Confidence Distribution\n")
    high = sum(1 for c in classifications if c['confidence'] >= 0.7)
    med = sum(1 for c in classifications if 0.4 <= c['confidence'] < 0.7)
    low = sum(1 for c in classifications if c['confidence'] < 0.4)
    lines.append(f"- High (>=0.7): {high} blocks")
    lines.append(f"- Medium (0.4-0.7): {med} blocks")
    lines.append(f"- Low (<0.4): {low} blocks")

    # Sub-type breakdown
    lines.append("\n## Sub-type Breakdown\n")
    sub_types = Counter(c.get('sub_type', 'unknown') for c in classifications)
    lines.append("| Sub-type | Count |")
    lines.append("|----------|-------|")
    for st, count in sorted(sub_types.items(), key=lambda x: -x[1]):
        lines.append(f"| {st} | {count} |")

    # Per-bank detail
    lines.append("\n## Per-Bank Detail\n")
    by_bank = {}
    for c in classifications:
        bank = c['bank']
        if bank not in by_bank:
            by_bank[bank] = []
        by_bank[bank].append(c)

    for bank in sorted(by_bank):
        bank_blocks = by_bank[bank]
        bank_cats = Counter(b['category'] for b in bank_blocks)
        cat_str = ', '.join(f"{cat}:{cnt}" for cat, cnt in sorted(bank_cats.items(), key=lambda x:-x[1]))
        lines.append(f"\n### Bank {bank} (0x{bank * 0x4000:05X})")
        lines.append(f"**{len(bank_blocks)} blocks reclassified** — {cat_str}\n")
        lines.append("| Offset | Category | Sub-type | Confidence | Entropy | Unique |")
        lines.append("|--------|----------|----------|------------|---------|--------|")
        for b in sorted(bank_blocks, key=lambda x: x['block_index']):
            lines.append(
                f"| {b['offset']} | {b['category']} | {b.get('sub_type', '-')} "
                f"| {b['confidence']:.3f} | {b['entropy']:.2f} | {b['unique_bytes']} |"
            )

    # Low confidence blocks for manual review
    low_conf = [c for c in classifications if c['confidence'] < 0.4]
    if low_conf:
        lines.append("\n## Low-Confidence Blocks (Manual Review Recommended)\n")
        lines.append("| Offset | Bank | Assigned | Confidence | All Scores |")
        lines.append("|--------|------|----------|------------|------------|")
        for c in sorted(low_conf, key=lambda x: x['confidence']):
            scores_str = ' '.join(f"{k}:{v:.2f}" for k, v in sorted(c['scores'].items(), key=lambda x:-x[1]))
            lines.append(f"| {c['offset']} | {c['bank']} | {c['category']} | {c['confidence']:.3f} | {scores_str} |")

    return '\n'.join(lines)


if __name__ == '__main__':
    rom_path = sys.argv[1] if len(sys.argv) > 1 else \
        '/home/computerstore/ROMs/gb/Yu-Gi-Oh! Monster Capsule GB (English).gbc'
    block_map_path = sys.argv[2] if len(sys.argv) > 2 else \
        '/home/computerstore/ygo-monster-capsule-gb-re/rom_analysis/block_map.json'

    print("Classifying mixed blocks...")
    results = classify_rom(rom_path, block_map_path)
    print(f"Classified {len(results)} blocks")

    # Generate report
    report = generate_report(results)
    print(report)

    # Output JSON results
    output_path = Path(block_map_path).parent / 'reclassification_results.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {output_path}")
