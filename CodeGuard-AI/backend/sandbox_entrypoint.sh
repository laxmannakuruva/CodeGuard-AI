#!/bin/sh
# Runs inside the sandbox container only.
set -e
cd /app

if [ -f requirements.txt ]; then
    pip install --user --no-cache-dir -r requirements.txt >/dev/null 2>&1 || true
fi

python3 -m pytest --tb=short -q . 2>&1
