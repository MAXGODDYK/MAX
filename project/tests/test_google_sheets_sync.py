from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists())
sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402
from app import initialize_local_database  # noqa: E402
from google_sheets_sync import GoogleSheetsSynchronizer, SyncConfig  # noqa: E402


class FakeSheetsClient:
    def __init__(self) -> None:
        self.tables = {table: [] for table in db.SYNC_TABLES}
        self.fail_next = False

    def ensure_structure(self) -> None:
        return None

    def read_all_tables(self):
        if self.fail_next:
            self.fail_next = False
            raise ConnectionError("offline")
        return copy.deepcopy(self.tables)

    def write_tables(self, tables):
        if self.fail_next:
            self.fail_next = False
            raise ConnectionError("offline")
        for table, rows in tables.items():
            self.tables[table] = copy.deepcopy(rows)


class GoogleSheetsSyncTests(unittest.TestCase):
    def make_sync(self):
        tempdir = tempfile.TemporaryDirectory()
        db_path = Path(tempdir.name) / "ingredients.db"
        credentials = Path(tempdir.name) / "service-account.json"
        credentials.write_text("{}", encoding="utf-8")
        db.init_db(db_path)
        client = FakeSheetsClient()
        config = SyncConfig(
            spreadsheet_id="fake-spreadsheet",
            credentials_path=str(credentials),
            sync_enabled=True,
        )
        sync = GoogleSheetsSynchronizer(db_path=db_path, config=config, client=client)
        self.addCleanup(tempdir.cleanup)
        return db_path, client, sync

    def first_row_key(self, db_path: Path, table: str) -> str:
        with db.session(db_path) as conn:
            return db.sync_row_key(table, db.sync_table_rows(conn, table)[0])

    def seller_for(self, db_path: Path, table: str, row_key: str) -> str:
        with db.session(db_path) as conn:
            row = conn.execute(f"SELECT seller FROM {table} WHERE id = ?", (int(row_key),)).fetchone()
            return row["seller"]

    def distilled_water_row(self, **overrides):
        row = {column: "" for column in db.SYNC_TABLE_COLUMNS["distilled_water"]}
        row.update(
            {
                "id": "1",
                "name": "Sync distilled water",
                "price_uah": "30",
                "package_amount_g": "1000",
                "seller": "Remote water seller",
                "grade": "distilled",
            }
        )
        row.update(overrides)
        return row

    def test_setup_exports_local_sqlite_to_google_rows(self) -> None:
        _db_path, client, sync = self.make_sync()
        result = sync.setup_remote_from_local()
        self.assertTrue(result.ok)
        self.assertGreater(len(client.tables["glycerin"]), 0)
        self.assertGreater(len(client.tables["recipes"]), 0)
        self.assertIn("distilled_water", client.tables)
        self.assertIn("tobacco_cuts", client.tables)
        self.assertIn("item_packagings", client.tables)
        self.assertGreater(len(client.tables["tobacco_cuts"]), 0)
        self.assertGreater(len(client.tables["item_packagings"]), 0)

    def test_remote_cache_startup_creates_empty_schema_without_samples(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        db_path = Path(tempdir.name) / "ingredients.db"

        class EnabledSync:
            enabled = True

        first_run = initialize_local_database(EnabledSync(), db_path)

        self.assertTrue(first_run)
        with db.session(db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tobacco").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tobacco_classifications").fetchone()[0], 0)

    def test_empty_remote_cache_pulls_rows_from_google_without_local_samples(self) -> None:
        source_db_path, client, source_sync = self.make_sync()
        setup_result = source_sync.setup_remote_from_local()
        self.assertTrue(setup_result.ok)

        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        target_db_path = Path(tempdir.name) / "ingredients.db"
        credentials = Path(tempdir.name) / "service-account.json"
        credentials.write_text("{}", encoding="utf-8")
        db.init_remote_cache_db(target_db_path)
        target_sync = GoogleSheetsSynchronizer(
            db_path=target_db_path,
            config=SyncConfig(
                spreadsheet_id="fake-spreadsheet",
                credentials_path=str(credentials),
                sync_enabled=True,
            ),
            client=client,
        )

        result = target_sync.sync_once()

        self.assertTrue(result.ok)
        self.assertGreater(len(db.list_recipes(target_db_path)), 0)
        with db.session(target_db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0], len(client.tables["recipes"]))
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM item_packagings").fetchone()[0],
                len(client.tables["item_packagings"]),
            )
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM flavors").fetchone()[0], 0)

    def test_setup_exports_distilled_water_rows(self) -> None:
        db_path, client, sync = self.make_sync()
        db.save_item(
            "distilled_water",
            {
                "name": "Local distilled water",
                "price_uah": 25,
                "package_amount_g": 1000,
                "seller": "Local water seller",
                "grade": "distilled",
            },
            db_path=db_path,
        )
        result = sync.setup_remote_from_local()
        self.assertTrue(result.ok)
        self.assertTrue(
            any(row["name"] == "Local distilled water" for row in client.tables["distilled_water"])
        )
        self.assertTrue(
            any(row["item_table"] == "distilled_water" for row in client.tables["item_packagings"])
        )

    def test_remote_change_is_pulled_to_sqlite(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        row_key = self.first_row_key(db_path, "glycerin")
        client.tables["glycerin"][0]["seller"] = "Remote seller"
        result = sync.sync_once()
        self.assertTrue(result.ok)
        self.assertEqual(self.seller_for(db_path, "glycerin", row_key), "Remote seller")

    def test_local_pending_change_is_pushed_to_google(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        row_key = self.first_row_key(db_path, "glycerin")
        with db.session(db_path) as conn:
            conn.execute("UPDATE glycerin SET seller = ? WHERE id = ?", ("Local seller", int(row_key)))
            db.mark_sync_pending_conn(conn, "glycerin", row_key, "upsert")
        result = sync.sync_once()
        self.assertTrue(result.ok)
        self.assertEqual(client.tables["glycerin"][0]["seller"], "Local seller")
        self.assertEqual(db.pending_sync_count(db_path), 0)

    def test_google_wins_when_local_and_remote_changed_same_row(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        row_key = self.first_row_key(db_path, "glycerin")
        with db.session(db_path) as conn:
            conn.execute("UPDATE glycerin SET seller = ? WHERE id = ?", ("Local seller", int(row_key)))
            db.mark_sync_pending_conn(conn, "glycerin", row_key, "upsert")
        client.tables["glycerin"][0]["seller"] = "Remote seller"
        result = sync.sync_once()
        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.conflicts, 1)
        self.assertEqual(self.seller_for(db_path, "glycerin", row_key), "Remote seller")

    def test_offline_queue_is_sent_after_recovery(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        row_key = self.first_row_key(db_path, "glycerin")
        with db.session(db_path) as conn:
            conn.execute("UPDATE glycerin SET seller = ? WHERE id = ?", ("Queued seller", int(row_key)))
            db.mark_sync_pending_conn(conn, "glycerin", row_key, "upsert")
        client.fail_next = True
        offline = sync.sync_once()
        self.assertFalse(offline.ok)
        self.assertGreater(db.pending_sync_count(db_path), 0)
        recovered = sync.sync_once()
        self.assertTrue(recovered.ok)
        self.assertEqual(client.tables["glycerin"][0]["seller"], "Queued seller")

    def test_distilled_water_remote_row_is_pulled_to_sqlite(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        client.tables["distilled_water"] = [self.distilled_water_row()]
        result = sync.sync_once()
        self.assertTrue(result.ok)
        rows = db.list_items("distilled_water", db_path=db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Sync distilled water")

    def test_distilled_water_local_row_is_pushed_to_google(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        db.save_item(
            "distilled_water",
            {
                "name": "Queued distilled water",
                "price_uah": 35,
                "package_amount_g": 1000,
                "seller": "Local water seller",
                "grade": "distilled",
            },
            db_path=db_path,
        )
        result = sync.sync_once()
        self.assertTrue(result.ok)
        self.assertTrue(
            any(row["name"] == "Queued distilled water" for row in client.tables["distilled_water"])
        )
        self.assertTrue(
            any(row["item_table"] == "distilled_water" for row in client.tables["item_packagings"])
        )

    def test_item_packaging_roundtrips_from_google(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        water = client.tables["distilled_water"][0]
        client.tables["item_packagings"] = [
            {
                "id": "1",
                "item_table": "distilled_water",
                "item_id": water["id"],
                "label": "500 г",
                "price_uah": "15",
                "package_amount_g": "500",
                "url": "https://example.test/water-500",
                "notes": "remote",
                "is_default": "1",
                "created_at": "",
                "updated_at": "",
            }
        ]
        result = sync.sync_once()
        self.assertTrue(result.ok)
        packagings = db.list_packagings("distilled_water", int(water["id"]), db_path=db_path)
        self.assertEqual(len(packagings), 1)
        self.assertEqual(packagings[0]["label"], "500 г")
        self.assertEqual(float(packagings[0]["price_uah"]), 15.0)
        item = db.get_item("distilled_water", int(water["id"]), db_path=db_path)
        self.assertEqual(float(item["package_amount_g"]), 500.0)

    def test_tobacco_cut_size_roundtrips_from_google(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        client.tables["tobacco"][0]["cut_size_mm"] = "20-40"
        result = sync.sync_once()
        self.assertTrue(result.ok)
        with db.session(db_path) as conn:
            row = conn.execute("SELECT cut_size_mm FROM tobacco WHERE id = ?", (int(client.tables["tobacco"][0]["id"]),)).fetchone()
        self.assertEqual(row["cut_size_mm"], "20-40")

    def test_recipe_item_tobacco_filters_roundtrip_from_google(self) -> None:
        db_path, client, sync = self.make_sync()
        sync.setup_remote_from_local()
        recipe_item = next(row for row in client.tables["recipe_items"] if row["ingredient_kind"] == "tobacco")
        recipe_item["tobacco_classification"] = "Virginia"
        recipe_item["tobacco_strength"] = "средняя"
        recipe_item["tobacco_cut"] = "Лапша"
        recipe_item["tobacco_cut_size_mm"] = "20 - 40 мм"
        result = sync.sync_once()
        self.assertTrue(result.ok)
        with db.session(db_path) as conn:
            row = conn.execute(
                """
                SELECT tobacco_classification, tobacco_strength, tobacco_cut, tobacco_cut_size_mm
                FROM recipe_items
                WHERE id = ?
                """,
                (int(recipe_item["id"]),),
            ).fetchone()
        self.assertEqual(row["tobacco_classification"], "Virginia")
        self.assertEqual(row["tobacco_strength"], "средняя")
        self.assertEqual(row["tobacco_cut"], "Лапша")
        self.assertEqual(row["tobacco_cut_size_mm"], "20-40")


if __name__ == "__main__":
    unittest.main()
