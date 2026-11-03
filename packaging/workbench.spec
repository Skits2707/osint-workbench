# PyInstaller spec — OSINT Verification Workbench
# Produces a single self-contained executable per OS.
# Templates and static assets are bundled; the SQLite DB is created at
# runtime next to the executable (so it lives on the USB stick).

import os

ROOT = os.path.dirname(os.path.abspath(SPECPATH))  # project root

datas = [
    (os.path.join(ROOT, "app", "templates"), "app/templates"),
    (os.path.join(ROOT, "app", "static"), "app/static"),
]

hidden = [
    "multipart",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "email.mime.text",
    "email.mime.multipart",
]

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython",
              "pypdfium2", "PyPDF2", "PIL", "Pillow",
              "numpy", "pandas", "matplotlib", "scipy"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="osint-workbench",
    debug=False,
    strip=False,
    upx=False,
    console=True,   # shows the local URL + stop instructions
)
