from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_DIR = next(
    (path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists()),
    None,
)

if APP_DIR is None:
    raise SystemExit("app.py was not found in a project subfolder.")

sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402
from google_sheets_sync import GoogleSheetsSynchronizer, SyncDisabled  # noqa: E402


def main() -> int:
    if not db.DB_PATH.exists():
        print("Local ingredients.db was not found.")
        print("This setup script uploads an existing local database to Google Sheets.")
        print("On a new device, configure google_sheets_config.json and run the app instead; it will download the cache from Google Sheets.")
        return 1

    db.init_db()
    synchronizer = GoogleSheetsSynchronizer()
    try:
        result = synchronizer.setup_remote_from_local()
    except SyncDisabled as exc:
        print(f"Google Sheets sync is not ready: {exc}")
        print("Copy google_sheets_config.example.json to google_sheets_config.json and fill it first.")
        return 1
    except Exception as exc:
        print(f"Google Sheets setup failed: {exc}")
        return 1

    print(result.message)
    print(f"Pushed rows: {result.pushed}")
    print(f"Pending rows: {result.pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
