@echo off
REM Build the Windows USB executable. Must be run ON Windows, from the project root.
python -m pip install -r requirements.txt pyinstaller
pyinstaller --clean packaging\workbench.spec
echo.
echo Built: dist\osint-workbench.exe
echo If SmartScreen warns on first run: More info -^> Run anyway.
echo (Common with unsigned PyInstaller builds; see README.)
