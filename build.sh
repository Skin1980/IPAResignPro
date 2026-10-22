#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== Building IPAResignPro Standalone macOS App ==="

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

pyinstaller --noconfirm IPAResignPro.spec

echo "=== Packaging IPAResignPro.app into zip with ditto ==="
rm -f dist/IPAResignPro_Standalone_Mac.zip
/usr/bin/ditto -c -k --keepParent dist/IPAResignPro.app dist/IPAResignPro_Standalone_Mac.zip

echo "=== Build finished successfully! ==="
echo "App bundle: dist/IPAResignPro.app"
echo "Zip archive: dist/IPAResignPro_Standalone_Mac.zip"
