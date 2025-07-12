@echo off
setlocal

REM === CONFIGURATION ===
set INPUT=kolyma.pdf
set OUTPUT=kolyma.inchworm

echo 🔧 Building Inchworm in release mode...
cargo build --release

echo 🚀 Running compression...
target\release\inchworm.exe c %INPUT% %OUTPUT% --status --collect-partials

echo ✅ Done!
echo   • Compressed: %OUTPUT%

endlocal
pause
