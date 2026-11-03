#!/usr/bin/env bash
# Build the Linux USB executable. Run from the project root:
#   bash packaging/build_linux.sh
set -euo pipefail
python3 -m pip install -r requirements.txt pyinstaller
pyinstaller --clean packaging/workbench.spec
echo
echo "Built: dist/osint-workbench"
echo "Copy dist/osint-workbench onto your USB stick (see README → USB setup)."
