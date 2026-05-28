#!/bin/bash

# Compare matching files in two directories and report
# lines that are new in the "new" directory versions.
#
# Usage:
#   ./compare_dirs.sh /path/to/old_dir /path/to/new_dir
#
# Example:
#   ./compare_dirs.sh ./old_output ./new_output

set -euo pipefail

OLD_DIR="${1:-}"
NEW_DIR="${2:-}"

if [[ -z "$OLD_DIR" || -z "$NEW_DIR" ]]; then
    echo "Usage: $0 OLD_DIR NEW_DIR"
    exit 1
fi

if [[ ! -d "$OLD_DIR" ]]; then
    echo "Error: OLD_DIR does not exist: $OLD_DIR"
    exit 1
fi

if [[ ! -d "$NEW_DIR" ]]; then
    echo "Error: NEW_DIR does not exist: $NEW_DIR"
    exit 1
fi

TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

echo "Comparing files..."
echo

find "$NEW_DIR" -type f | while read -r NEW_FILE; do

    # Relative path inside NEW_DIR
    REL_PATH="${NEW_FILE#$NEW_DIR/}"

    OLD_FILE="$OLD_DIR/$REL_PATH"

    echo "=================================================="
    echo "File: $REL_PATH"

    if [[ ! -f "$OLD_FILE" ]]; then
        echo "No matching old file found."
        echo "Entire file is new:"
        cat "$NEW_FILE"
        echo
        continue
    fi

    OLD_SORTED="$TMP_DIR/old.sorted"
    NEW_SORTED="$TMP_DIR/new.sorted"

    sort "$OLD_FILE" > "$OLD_SORTED"
    sort "$NEW_FILE" > "$NEW_SORTED"

    NEW_LINES=$(comm -13 "$OLD_SORTED" "$NEW_SORTED")

    if [[ -n "$NEW_LINES" ]]; then
        echo "New lines:"
        echo "$NEW_LINES"
    else
        echo "No new lines."
    fi

    echo
done
