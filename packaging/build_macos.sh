#!/usr/bin/env bash
# Build the macOS USB executable. Must be run ON macOS, from the project root.
set -euo pipefail
python3 -m pip install -r requirements.txt pyinstaller
pyinstaller --clean packaging/workbench.spec
echo
echo "Built: dist/osint-workbench"
echo "Note: unsigned builds may require right-click → Open on first run"
echo "(Gatekeeper). See README for details."
