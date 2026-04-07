#!/bin/bash
# Yu-Gi-Oh! Monster Capsule GB — Grind Bot
# Automates capsule purchasing and basic battle grinding
# Requires: RetroArch running with mGBA core, cheats enabled
#
# Usage: ./capsule-grind-bot.sh [mode]
#   purchase - spam A to buy capsules from a machine
#   battle   - auto-battle (select first monster, attack nearest enemy)
#   idle     - just hold A to advance dialogue

set -uo pipefail
MODE="${1:-purchase}"
DISPLAY=:1

echo "Monster Capsule GB Grind Bot — Mode: $MODE"
echo "Make sure RetroArch is focused and cheats are ON"
echo "Press Ctrl+C to stop"
echo ""

# Focus RetroArch
wmctrl -a "RetroArch" 2>/dev/null
sleep 1

case $MODE in
  purchase)
    echo "=== Capsule Purchase Mode ==="
    echo "Stand in front of a capsule machine before starting"
    echo "Bot will spam A to buy capsules continuously"
    echo ""
    CYCLES=0
    while true; do
      # Press A to interact/confirm purchase
      xdotool key z
      sleep 0.3
      xdotool key z
      sleep 0.3
      xdotool key z
      sleep 0.5
      # Sometimes need to dismiss text
      xdotool key z
      sleep 0.3
      CYCLES=$((CYCLES + 1))
      [ $((CYCLES % 50)) -eq 0 ] && echo "  $CYCLES purchase cycles..."
    done
    ;;

  battle)
    echo "=== Battle Mode ==="
    echo "Bot will select first available monster and attack"
    echo ""
    while true; do
      # Confirm / select monster
      xdotool key z
      sleep 0.8
      # Move cursor (try right to find enemy)
      xdotool key Right
      sleep 0.3
      xdotool key Right
      sleep 0.3
      # Confirm attack
      xdotool key z
      sleep 0.8
      # Confirm target
      xdotool key z
      sleep 1.0
      # Wait for animation
      sleep 1.5
      # Advance any dialogue
      xdotool key z
      sleep 0.5
    done
    ;;

  idle)
    echo "=== Idle/Dialogue Advance Mode ==="
    echo "Spams A to advance all text"
    echo ""
    while true; do
      xdotool key z
      sleep 0.4
    done
    ;;

  turbo)
    echo "=== Turbo Mode ==="
    echo "Hold fast-forward + spam A"
    echo "Press F1 first and set fast-forward to a hotkey"
    echo ""
    # Enable fast-forward
    xdotool keydown space
    while true; do
      xdotool key z
      sleep 0.1
    done
    ;;

  *)
    echo "Unknown mode: $MODE"
    echo "Modes: purchase, battle, idle, turbo"
    exit 1
    ;;
esac
