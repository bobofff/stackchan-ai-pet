#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uvicorn app.main:app --app-dir brain --host 0.0.0.0 --port 8787 --reload

