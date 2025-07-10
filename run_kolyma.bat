@echo off
setlocal

REM === CONFIGURATION ===
set INPUT=kolyma.pdf
set OUTPUT=kolyma.inchworm
set GLOSS=gloss.bin

echo 🔧 Building Inchworm in release mode...
cargo build --release

echo 🚀 Running compression...
cargo run --release --bin compressor -- compress %INPUT% %OUTPUT% --gloss %GLOSS% --status

IF EXIST target\release\gloss_debug_dump.exe (
    echo 📤 Exporting gloss to gloss_dump.csv...
    target\release\gloss_debug_dump.exe %GLOSS% gloss_dump.csv
)

echo ✅ Done!
echo   • Compressed: %OUTPUT%
echo   • Gloss:      %GLOSS%
echo   • CSV:        gloss_dump.csv (if available)

endlocal
pause
