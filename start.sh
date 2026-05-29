#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo ""
echo " paperlibrary"
echo " ============"

# Check Python (try python3 first, fall back to python)
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo ""
    echo " ERROR: Python not found."
    echo " Please install Python 3.11+ from https://python.org/downloads/"
    echo ""
    exit 1
fi

# Install / update dependencies
echo " Checking dependencies..."
"$PYTHON" -m pip install -r requirements.txt -q

echo " Starting..."
echo ""
"$PYTHON" -m paperlibrary
