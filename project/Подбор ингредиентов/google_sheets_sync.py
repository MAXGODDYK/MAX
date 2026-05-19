from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import database as db


PROJECT_DIR = db.BASE_DIR.parent
CONFIG_PATH = PROJECT_DIR / "google_sheets_config.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LOCAL_SCHEMA_EXPANSION_COLUMNS = {
    "tobacco": {"cut_size_mm"},
    "recipe_items": {"tobacco_classification", "tobacco_strength", "tobacco_cut", "tobacco_cut_size_mm"},
}


class SyncDisabled(RuntimeError):
    pass


@dataclass
class SyncConfig:
    spreadsheet_id: str = ""
    credentials_path: str = "secrets/google_service_account.json"
    sync_enabled: bool = False

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "SyncConfig":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            spreadsheet_id=str(data.get("spreadsheet_id", "")).strip(),
            credentials_path=str(data.get("credentials_path", "secrets/google_service_account.json")).strip(),
            sync_enabled=bool(data.get("sync_enabled", False)),
        )

    def credentials_file(self, config_path: Path = CONFIG_PATH) -> Path:
        path = Path(self.credentials_path)
        if not path.is_absolute():
            path = config_path.parent / path
        return path

    def validate(self) -> None:
        if not self.sync_enabled:
            raise SyncDisabled("Google Sheets sync is disabled in google_sheets_config.json.")
        if not self.spreadsheet_id:
            raise SyncDisabled("spreadsheet_id is empty in google_sheets_config.json.")
        credentials = self.credentials_file()
        if not credentials.exists():
            raise SyncDisabled(f"Google service account JSON was not found: {credentials}")


@dataclass
class SyncResult:
    ok: bool
    status: str
    message: str
    pulled: int = 0
    pushed: int = 0
    conflicts: int = 0
    pending: int = 0

    def label(self) -> str:
        if self.status == "disabled":
            return "Синхронизация не настроена"
        if self.status == "offline":
            return f"Нет интернета / ошибка Google. В очереди: {self.pending}"
        if self.conflicts:
            return f"Конфликт: Google-версия применена. В очереди: {self.pending}"
        if self.pending:
            return f"Ожидает отправки: {self.pending}"
        return "Синхронизировано"


def sheet_range(sheet_name: str, a1_range: str) -> str:
    safe_name = sheet_name.replace("'", "''")
    return f"'{safe_name}'!{a1_range}"


class GoogleSheetsClient:
    def __init__(self, config: SyncConfig) -> None:
        config.validate()
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise SyncDisabled(
                "Google API libraries are not installed. Run: py -m pip install -r requirements.txt"
            ) from exc

        credentials = Credentials.from_service_account_file(str(config.credentials_file()), scopes=SCOPES)
        self.spreadsheet_id = config.spreadsheet_id
        self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _execute(self, request):
        delay = 1.0
        for attempt in range(5):
            try:
                return request.execute()
            except Exception as exc:
                status = getattr(getattr(exc, "resp", None), "status", None)
                retryable = status in {429, 500, 502, 503, 504} or status is None
                if not retryable or attempt == 4:
                    raise
                time.sleep(delay + random.random())
                delay = min(delay * 2, 32)
        raise RuntimeError("Google Sheets request failed after retries.")

    def ensure_structure(self) -> None:
        metadata = self._execute(self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id))
        existing = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}
        requests = [
            {"addSheet": {"properties": {"title": table}}}
            for table in db.SYNC_TABLES
            if table not in existing
        ]
        if requests:
            self._execute(
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": requests},
                )
            )
        for table in db.SYNC_TABLES:
            self._write_header(table)

    def _write_header(self, table: str) -> None:
        self._execute(
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_range(table, "1:1"),
                valueInputOption="RAW",
                body={"values": [db.SYNC_TABLE_COLUMNS[table]]},
            )
        )

    def read_all_tables(self) -> dict[str, list[dict[str, Any]]]:
        tables: dict[str, list[dict[str, Any]]] = {}
        for table in db.SYNC_TABLES:
            result = self._execute(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_range(table, "A:ZZ"),
                    valueRenderOption="UNFORMATTED_VALUE",
                )
            )
            values = result.get("values", [])
            tables[table] = self._rows_from_values(table, values)
        return tables

    def _rows_from_values(self, table: str, values: list[list[Any]]) -> list[dict[str, Any]]:
        expected = db.SYNC_TABLE_COLUMNS[table]
        if not values:
            return []
        headers = [str(value).strip() for value in values[0]]
        index_by_header = {header: index for index, header in enumerate(headers)}
        rows: list[dict[str, Any]] = []
        for raw in values[1:]:
            row = {column: "" for column in expected}
            for column in expected:
                index = index_by_header.get(column)
                if index is not None and index < len(raw):
                    row[column] = raw[index]
            if any(str(value).strip() for value in row.values()):
                rows.append(row)
        return rows

    def write_tables(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        for table, rows in tables.items():
            self._execute(
                self.service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_range(table, "A:ZZ"),
                    body={},
                )
            )
            values = [db.SYNC_TABLE_COLUMNS[table]]
            for row in rows:
                values.append([db.normalize_sync_value(column, row.get(column)) for column in db.SYNC_TABLE_COLUMNS[table]])
            self._execute(
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_range(table, "A1"),
                    valueInputOption="RAW",
                    body={"values": values},
                )
            )


class GoogleSheetsSynchronizer:
    def __init__(
        self,
        db_path: Path = db.DB_PATH,
        config: SyncConfig | None = None,
        client: Any | None = None,
    ) -> None:
        self.db_path = db_path
        self.config = config or SyncConfig.load()
        self._client = client

    @property
    def enabled(self) -> bool:
        return self.config.sync_enabled

    def client(self):
        if self._client is None:
            self._client = GoogleSheetsClient(self.config)
        return self._client

    def disabled_result(self, message: str) -> SyncResult:
        return SyncResult(ok=False, status="disabled", message=message, pending=self.pending_count())

    def pending_count(self) -> int:
        try:
            return db.pending_sync_count(self.db_path)
        except Exception:
            return 0

    def sync_once(self) -> SyncResult:
        try:
            self.config.validate()
        except SyncDisabled as exc:
            return self.disabled_result(str(exc))

        try:
            client = self.client()
            client.ensure_structure()
            remote_tables = client.read_all_tables()
            result, tables_to_push = self._merge_remote_into_local(remote_tables)
            if tables_to_push:
                client.write_tables(tables_to_push)
                self._mark_tables_synced(tables_to_push)
                result.pushed += sum(len(rows) for rows in tables_to_push.values())
            result.pending = self.pending_count()
            if result.pending and result.status == "synced":
                result.status = "pending"
            return result
        except Exception as exc:
            self._mark_pending_error(str(exc))
            return SyncResult(
                ok=False,
                status="offline",
                message=str(exc),
                pending=self.pending_count(),
            )

    def setup_remote_from_local(self) -> SyncResult:
        self.config.validate()
        client = self.client()
        client.ensure_structure()
        with db.session(self.db_path) as conn:
            db.ensure_sync_tables(conn)
            local_tables = db.sync_all_rows(conn)
        client.write_tables(local_tables)
        self._mark_tables_synced(local_tables)
        return SyncResult(
            ok=True,
            status="synced",
            message="Google Sheet initialized from local SQLite.",
            pushed=sum(len(rows) for rows in local_tables.values()),
            pending=self.pending_count(),
        )

    def _merge_remote_into_local(
        self,
        remote_tables: dict[str, list[dict[str, Any]]],
    ) -> tuple[SyncResult, dict[str, list[dict[str, Any]]]]:
        result = SyncResult(ok=True, status="synced", message="Синхронизация завершена.")
        dirty_tables: set[str] = set()

        with db.session(self.db_path) as conn:
            db.ensure_sync_tables(conn)
            remote_tables = self._prepare_remote_rows(conn, remote_tables, dirty_tables)
            states = self._load_states(conn)

            for table in db.SYNC_TABLES:
                remote_by_key = {
                    db.sync_row_key(table, row): row
                    for row in remote_tables.get(table, [])
                    if db.sync_row_key_from_values(table, row)
                }
                local_by_key = {db.sync_row_key(table, row): row for row in db.sync_table_rows(conn, table)}

                for row_key, remote_row in remote_by_key.items():
                    remote_hash = db.sync_row_hash(table, remote_row)
                    local_row = local_by_key.get(row_key)
                    local_hash = db.sync_row_hash(table, local_row) if local_row else None
                    state = states.get((table, row_key))
                    if state is None and local_row is not None and local_hash == remote_hash:
                        self._set_state(conn, table, row_key, remote_hash, local_hash, "synced", None)
                        continue
                    pending_op = state["pending_op"] if state else None
                    remote_changed = state is None or remote_hash != state["remote_hash"]
                    local_changed = local_row is not None and state is not None and local_hash != state["local_hash"]
                    local_schema_expansion = (
                        local_row is not None
                        and state is not None
                        and remote_changed
                        and local_changed
                        and self._is_local_schema_expansion_change(table, local_row, remote_row)
                    )

                    if pending_op == "delete":
                        if remote_changed:
                            db.upsert_sync_row(conn, table, remote_row)
                            self._set_state(conn, table, row_key, remote_hash, remote_hash, "conflict", None)
                            result.conflicts += 1
                            result.pulled += 1
                        else:
                            dirty_tables.add(table)
                        continue

                    if pending_op == "upsert":
                        if remote_changed:
                            db.upsert_sync_row(conn, table, remote_row)
                            self._set_state(conn, table, row_key, remote_hash, remote_hash, "conflict", None)
                            result.conflicts += 1
                            result.pulled += 1
                        else:
                            dirty_tables.add(table)
                        continue

                    if local_schema_expansion:
                        dirty_tables.add(table)
                        continue

                    if remote_changed:
                        if local_row is not None and (state is None or local_changed):
                            result.conflicts += 1
                        else:
                            result.pulled += 1
                        db.upsert_sync_row(conn, table, remote_row)
                        self._set_state(conn, table, row_key, remote_hash, remote_hash, "synced", None)
                    elif local_changed:
                        dirty_tables.add(table)
                    elif state is None:
                        self._set_state(conn, table, row_key, remote_hash, local_hash or remote_hash, "synced", None)

                local_by_key = {db.sync_row_key(table, row): row for row in db.sync_table_rows(conn, table)}
                for row_key, local_row in local_by_key.items():
                    if row_key in remote_by_key:
                        continue
                    state = states.get((table, row_key))
                    if state and state["pending_op"] == "upsert":
                        dirty_tables.add(table)
                    elif state and state["remote_hash"]:
                        db.delete_sync_row(conn, table, row_key)
                        self._delete_state(conn, table, row_key)
                        result.pulled += 1
                        if state["pending_op"]:
                            result.conflicts += 1
                    else:
                        dirty_tables.add(table)

                for (state_table, row_key), state in states.items():
                    if state_table != table or row_key == db.SYNC_TABLE_MARKER:
                        continue
                    if state["pending_op"] == "delete" and row_key not in local_by_key:
                        if row_key in remote_by_key:
                            dirty_tables.add(table)
                        else:
                            self._delete_state(conn, table, row_key)

                if (table, db.SYNC_TABLE_MARKER) in states:
                    dirty_tables.add(table)

            self._refresh_tobacco_cache(conn)
            dirty_tables.update(db.repair_item_packagings_conn(conn))
            tables_to_push = {table: db.sync_table_rows(conn, table) for table in dirty_tables}

        return result, tables_to_push

    def _is_local_schema_expansion_change(self, table: str, local_row: dict[str, Any], remote_row: dict[str, Any]) -> bool:
        local_only_columns = LOCAL_SCHEMA_EXPANSION_COLUMNS.get(table)
        if not local_only_columns:
            return False
        for column in db.SYNC_TABLE_COLUMNS[table]:
            local_value = db.normalize_sync_value(column, local_row[column])
            remote_value = db.normalize_sync_value(column, remote_row.get(column))
            if local_value == remote_value:
                continue
            if column in local_only_columns and remote_value == "":
                continue
            return False
        return True

    def _prepare_remote_rows(
        self,
        conn,
        remote_tables: dict[str, list[dict[str, Any]]],
        dirty_tables: set[str],
    ) -> dict[str, list[dict[str, Any]]]:
        prepared: dict[str, list[dict[str, Any]]] = {}
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for table in db.SYNC_TABLES:
            rows: list[dict[str, Any]] = []
            next_id = db.next_sync_id(conn, table) if db.SYNC_PRIMARY_KEYS[table] == ("id",) else 0
            if db.SYNC_PRIMARY_KEYS[table] == ("id",):
                remote_ids = [
                    int(float(str(row.get("id")).strip()))
                    for row in remote_tables.get(table, [])
                    if str(row.get("id", "")).strip()
                ]
                if remote_ids:
                    next_id = max(next_id, max(remote_ids) + 1)
            for row in remote_tables.get(table, []):
                row = dict(row)
                if db.SYNC_PRIMARY_KEYS[table] == ("id",) and not str(row.get("id", "")).strip():
                    if any(str(value).strip() for column, value in row.items() if column != "id"):
                        row["id"] = next_id
                        next_id += 1
                        dirty_tables.add(table)
                if "created_at" in row and not str(row.get("created_at", "")).strip():
                    row["created_at"] = now
                    dirty_tables.add(table)
                if "updated_at" in row and not str(row.get("updated_at", "")).strip():
                    row["updated_at"] = now
                    dirty_tables.add(table)
                if db.sync_row_key_from_values(table, row):
                    rows.append(row)
            prepared[table] = rows
        return prepared

    def _load_states(self, conn) -> dict[tuple[str, str], Any]:
        rows = conn.execute("SELECT * FROM sync_state").fetchall()
        return {(row["table_name"], row["row_key"]): row for row in rows}

    def _set_state(
        self,
        conn,
        table: str,
        row_key: str,
        remote_hash: str | None,
        local_hash: str | None,
        status: str,
        pending_op: str | None,
        last_error: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO sync_state
                (table_name, row_key, remote_hash, local_hash, pending_op, status, last_error, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(table_name, row_key) DO UPDATE SET
                remote_hash = excluded.remote_hash,
                local_hash = excluded.local_hash,
                pending_op = excluded.pending_op,
                status = excluded.status,
                last_error = excluded.last_error,
                updated_at = CURRENT_TIMESTAMP
            """,
            (table, row_key, remote_hash, local_hash, pending_op, status, last_error),
        )

    def _delete_state(self, conn, table: str, row_key: str) -> None:
        conn.execute("DELETE FROM sync_state WHERE table_name = ? AND row_key = ?", (table, row_key))

    def _mark_tables_synced(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        with db.session(self.db_path) as conn:
            db.ensure_sync_tables(conn)
            for table in tables:
                conn.execute("DELETE FROM sync_state WHERE table_name = ?", (table,))
                for row in db.sync_table_rows(conn, table):
                    row_key = db.sync_row_key(table, row)
                    row_hash = db.sync_row_hash(table, row)
                    self._set_state(conn, table, row_key, row_hash, row_hash, "synced", None)

    def _mark_pending_error(self, error: str) -> None:
        with db.session(self.db_path) as conn:
            db.ensure_sync_tables(conn)
            conn.execute(
                """
                UPDATE sync_state
                SET status = 'error', last_error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE pending_op IS NOT NULL
                """,
                (error,),
            )

    def _refresh_tobacco_cache(self, conn) -> None:
        db.sync_all_tobacco_classification_cache(conn)
