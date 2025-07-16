@echo off
setlocal

REM === CONFIGURATION ===
set INPUT=kolyma.pdf
set OUTPUT=kolyma.tlmr

echo 🔧 Building Telomere in release mode...
cargo build --release

echo 🚀 Running compression...
target\release\telomere.exe c %INPUT% %OUTPUT% --status --collect-partials

echo ✅ Done!
echo   • Compressed: %OUTPUT%

endlocal
pause
