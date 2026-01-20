#!/bin/bash
# Run a ROM in the emulator

ROM_FILE=$1
EMULATOR=${2:-sameboy}

if [ -z "$ROM_FILE" ]; then
    echo "Usage: run.sh <rom-file> [emulator]"
    echo "Emulators: sameboy (default), mgba, bgb"
    exit 1
fi

# Resolve to absolute path
if [ ! -f "$ROM_FILE" ]; then
    echo "Error: ROM file not found: $ROM_FILE"
    exit 1
fi

ROM_FILE=$(cd "$(dirname "$ROM_FILE")" && pwd)/$(basename "$ROM_FILE")

echo "Launching $ROM_FILE in $EMULATOR..."

case $EMULATOR in
    sameboy)
        open -a SameBoy "$ROM_FILE"
        ;;
    mgba)
        mgba "$ROM_FILE" &
        ;;
    bgb)
        if [ -f ~/.wine/drive_c/bgb/bgb.exe ]; then
            wine ~/.wine/drive_c/bgb/bgb.exe "$ROM_FILE" &
        else
            echo "BGB not found. Install it to ~/.wine/drive_c/bgb/"
            exit 1
        fi
        ;;
    *)
        echo "Unknown emulator: $EMULATOR"
        echo "Available: sameboy, mgba, bgb"
        exit 1
        ;;
esac
