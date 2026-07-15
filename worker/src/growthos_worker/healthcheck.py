from __future__ import annotations

import sys
import time

from growthos_worker.settings import WorkerSettings


def main() -> None:
    settings = WorkerSettings.from_env()
    try:
        age = time.time() - settings.heartbeat_file.stat().st_mtime
    except FileNotFoundError:
        raise SystemExit("worker heartbeat not found") from None
    if age > settings.heartbeat_max_age_seconds:
        raise SystemExit(f"worker heartbeat is stale ({age:.1f}s)")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
