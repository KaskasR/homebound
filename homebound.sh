#!/bin/sh
# Start Homebound. Usage: ./homebound.sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "First run: creating virtualenv and installing requirements..."
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt || exit 1
fi
exec .venv/bin/python -m homebound "$@"
