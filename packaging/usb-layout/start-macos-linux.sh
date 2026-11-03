#!/usr/bin/env bash
# USB launcher — macOS / Linux (auto-detects)
cd "$(dirname "$0")"
case "$(uname -s)" in
  Darwin) exec ./macos/osint-workbench ;;
  Linux)  exec ./linux/osint-workbench ;;
  *) echo "Unsupported OS: $(uname -s)"; exit 1 ;;
esac
