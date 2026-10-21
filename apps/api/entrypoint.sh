#!/bin/sh
set -eu

echo "Oportuna API: applying database migrations..."
python - <<'PY'
import time
import sys

from sqlalchemy import create_engine, text

from oportuna.config import get_settings

engine = create_engine(get_settings().database_url)
for attempt in range(30):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("database reachable")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"database not ready ({attempt + 1}/30): {type(exc).__name__}")
        time.sleep(2)
else:
    print("database unreachable", file=sys.stderr)
    sys.exit(1)
PY

alembic upgrade head
python -m oportuna.seed

exec uvicorn oportuna.main:app --host 0.0.0.0 --port 8000 --proxy-headers
