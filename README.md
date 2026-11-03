# OSINT Verification Workbench

A portable, local-first OSINT tool: give it an identifier (username, email,
domain, or name) and it queries **public sources only**, correlates the
results, and produces a **sourced, confidence-scored verification report**.
Includes a second tool — portable **File Search** with full-text content
indexing — in the same app. Everything runs from a USB stick.

Built as a portfolio project demonstrating OSINT pipeline design, entity
resolution, and responsible-data-handling principles.

![status](https://img.shields.io/badge/status-MVP-blue)

## What it does

```
identifier (email / username / domain / name)
   │
   ▼
[1] Collectors ─ one plugin per public source, run concurrently
   │            username search · GitHub API · Gravatar · HIBP breaches
   │            crt.sh (CT logs) · Wayback Machine · RDAP registry data
   ▼
[2] Normaliser ─ every result becomes a Finding with provenance:
   │             { fact, source URL, evidence snippet, retrieved-at, confidence }
   ▼
[3] Correlation engine ─ links accounts across platforms, boosts corroborated
   │                      findings, flags contradictions (e.g. two locations)
   ▼
[4] Report ─ dashboard + printable report with an overall verdict
             (STRONG / MODERATE / WEAK verification, with reasoning)
```

### Deliberate design choices (the compliance section)

- **Public sources only.** No login scraping, no platform-ToS violations, no
  data-broker purchases. Sources are curated for reliable detection.
- **Full provenance.** Every fact links back to its source with a retrieval
  timestamp and an evidence excerpt. Nothing is asserted without a citation.
- **Honest coverage.** If a source wasn't checked (e.g. no HIBP API key, or a
  source unreachable from the current network), the report says so instead
  of staying silent.
- **Local-first data.** The SQLite database and all reports live next to the
  executable. Nothing is sent anywhere except the requests to the public
  sources themselves. Deleting an investigation deletes its findings.
- **Intended use:** auditing your own footprint (self-OSINT), consented
  verification work, or researching threat actors in legitimate security work.

## Running from a USB stick (the whole point)

The app packages into a single self-contained executable per OS — no Python,
no install, no admin rights. The host laptop needs only a browser.

### USB layout

```
USB stick/
├── start-windows.bat          ← double-click on Windows
├── start-macos-linux.sh       ← run this on macOS / Linux
├── windows/osint-workbench.exe
├── macos/osint-workbench
├── linux/osint-workbench
└── data/                      ← created on first run; your database lives here
```

1. Build the executables (below), or download them from CI artifacts.
2. Copy them into the folder structure above (launchers in `packaging/usb-layout/`).
3. Plug into any laptop, run the launcher for that OS — the dashboard opens
   in the browser automatically at `http://127.0.0.1:8000`.

### Building the executables

You cannot cross-compile PyInstaller executables — build on each target OS,
or use CI (see below).

| OS      | Command                              |
|---------|--------------------------------------|
| Windows | `packaging\build_windows.bat`        |
| macOS   | `bash packaging/build_macos.sh`      |
| Linux   | `bash packaging/build_linux.sh`      |

### CI auto-builds (one manual step)

`packaging/ci-build.yml` contains a GitHub Actions workflow that builds all
three executables automatically. GitHub blocks API tokens from installing
workflow files, so activate it once by hand:

1. In this repo on github.com: **Add file → Create new file**
2. Name it exactly `.github/workflows/build.yml`
3. Paste the contents of `packaging/ci-build.yml`, commit

Then every push builds all three executables — find them under
**Actions → latest run → Artifacts** (`usb-windows` is the .exe you want).

**Windows SmartScreen / antivirus:** unsigned PyInstaller builds are a known
false-positive target. Click *More info → Run anyway*, or sign the exe.
This is normal for hobby security tools.

**macOS Gatekeeper:** first run may need right-click → Open.

## Tool 2: File Search (built into the same app)

Windows Search barely works on USB drives and refuses to index network
shares. The workbench ships a second tool — **File Search** — that builds
its own index into the same on-stick database:

- Point it at any folder, drive, or `\\server\share` path — it indexes
  filenames, sizes and dates for everything beneath it.
- Optionally indexes **file contents** (text files, code, CSV, Markdown,
  **.docx** and **.pdf**) into an SQLite FTS5 full-text index, so
  "files containing *kerberos renewal*" answers instantly.
- Strictly read-only against scanned drives; the index travels on the stick.
- Open it from the **File Search** tab in the dashboard.

## Development mode

```bash
pip install -r requirements.txt
python run.py              # opens http://127.0.0.1:8000
```

Optional: set `HIBP_API_KEY` to enable HaveIBeenPwned breach lookups
(official paid API). Without it, the report notes the check was skipped.

## Adding a collector (plugin architecture)

```python
# app/collectors/mysource.py
from .base import Collector
from ..models import Finding

class MySourceCollector(Collector):
    name = "mysource"
    supported_inputs = ("username",)

    async def collect(self, input_type, value, client):
        ...  # return [Finding(...)]
```

Register it in `app/collectors/__init__.py` — the scanner, database,
correlation engine, and report pick it up automatically.

## Roadmap

- [x] Domain input type (crt.sh certificate transparency, RDAP, Wayback)
- [x] Portable file search with full-text content indexing
- [ ] Entity-relationship graph view (Cytoscape.js, vendored locally)
- [ ] PDF report export (currently: browser print → PDF)
- [ ] Avatar-hash matching across platforms (perceptual hashing)
- [ ] Case notes: analyst annotations attached to findings
- [ ] Export to JSON/CSV for chaining with other tools
- [ ] File search: filename filters (extension, size, date ranges)

## Legal & ethical note

This tool aggregates information that is already public, but compiling a
profile of an identifiable person may still be regulated processing of
personal data (e.g. UK GDPR / GDPR). Use it on your own identifiers, with the
subject's consent, or against malicious actors in legitimate security
research. You are responsible for how you use it.
