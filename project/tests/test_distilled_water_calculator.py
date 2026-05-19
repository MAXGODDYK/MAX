from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists())
sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402


class DistilledWaterCalculatorTests(unittest.TestCase):
    def make_db(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tempdir = tempfile.TemporaryDirectory()
        db_path = Path(tempdir.name) / "ingredients.db"
        db.init_db(db_path)
        self.addCleanup(tempdir.cleanup)
        return tempdir, db_path

    def save_water(self, db_path: Path, name: str = "Distilled water", price: float = 20) -> int:
        return db.save_item(
            "distilled_water",
            {
                "name": name,
                "price_uah": price,
                "package_amount_g": 1000,
                "seller": "Test seller",
                "grade": "distilled",
            },
            db_path=db_path,
        )

    def first_tobacco_ids(self, db_path: Path, count: int = 1) -> list[int]:
        return [int(row["id"]) for row in db.list_items("tobacco", db_path=db_path)[:count]]

    def default_packaging_id(self, table_key: str, item_id: int, db_path: Path) -> int:
        return int(db.list_packagings(table_key, item_id, db_path=db_path)[0]["id"])

    def test_init_db_creates_distilled_water_table(self) -> None:
        _tempdir, db_path = self.make_db()
        with db.session(db_path) as conn:
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'distilled_water'"
            ).fetchone()
        self.assertIsNotNone(table)
        self.assertIn("distilled_water", db.SYNC_TABLES)
        self.assertEqual(db.KIND_TO_TABLE_KEY["distilled_water"], "distilled_water")

    def test_existing_recipe_items_survive_kind_constraint_migration(self) -> None:
        _tempdir, db_path = self.make_db()
        with db.session(db_path) as conn:
            conn.execute("DELETE FROM recipe_items WHERE ingredient_kind = 'distilled_water'")
            before = conn.execute("SELECT COUNT(*) FROM recipe_items").fetchone()[0]
            conn.execute("DROP INDEX IF EXISTS idx_recipe_items_recipe")
            conn.execute("ALTER TABLE recipe_items RENAME TO recipe_items_old_constraint")
            conn.execute(
                """
                CREATE TABLE recipe_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    ingredient_kind TEXT NOT NULL CHECK (
                        ingredient_kind IN ('tobacco', 'glycerin', 'gfs', 'propylene_glycol', 'flavor')
                    ),
                    label TEXT NOT NULL CHECK (length(trim(label)) > 0),
                    percent REAL NOT NULL CHECK (percent >= 0 AND percent <= 100)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO recipe_items (id, recipe_id, ingredient_kind, label, percent)
                SELECT id, recipe_id, ingredient_kind, label, percent
                FROM recipe_items_old_constraint
                """
            )
            conn.execute("DROP TABLE recipe_items_old_constraint")
            conn.execute("CREATE INDEX idx_recipe_items_recipe ON recipe_items(recipe_id)")

        db.init_db(db_path)
        with db.session(db_path) as conn:
            after = conn.execute("SELECT COUNT(*) FROM recipe_items").fetchone()[0]
            schema = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'recipe_items'"
            ).fetchone()["sql"]
        self.assertEqual(after, before)
        self.assertIn("distilled_water", schema)

    def test_save_recipe_accepts_distilled_water(self) -> None:
        _tempdir, db_path = self.make_db()
        recipe_id = db.save_recipe(
            {"name": "Water recipe"},
            [
                {"ingredient_kind": "tobacco", "label": "Leaf", "percent": 50},
                {"ingredient_kind": "distilled_water", "label": "Water", "percent": 50},
            ],
            db_path=db_path,
        )
        kinds = [row["ingredient_kind"] for row in db.get_recipe_items(recipe_id, db_path=db_path)]
        self.assertEqual(kinds, ["tobacco", "distilled_water"])

    def test_calculate_recipe_counts_distilled_water_cost(self) -> None:
        _tempdir, db_path = self.make_db()
        water_id = self.save_water(db_path, price=20)
        tobacco_id = self.first_tobacco_ids(db_path)[0]
        recipe_id = db.save_recipe(
            {"name": "Water cost recipe"},
            [
                {"ingredient_kind": "tobacco", "label": "Leaf", "percent": 50},
                {"ingredient_kind": "distilled_water", "label": "Water", "percent": 50},
            ],
            db_path=db_path,
        )
        water_packaging_id = self.default_packaging_id("distilled_water", water_id, db_path)
        tobacco_packaging_id = self.default_packaging_id("tobacco", tobacco_id, db_path)
        selections = {
            int(row["id"]): water_packaging_id if row["ingredient_kind"] == "distilled_water" else tobacco_packaging_id
            for row in db.get_recipe_items(recipe_id, db_path=db_path)
        }

        rows, total_cost = db.calculate_recipe(recipe_id, 100, selections, db_path=db_path)

        water_row = next(row for row in rows if row["kind"] == "distilled_water")
        self.assertAlmostEqual(water_row["grams"], 50)
        self.assertAlmostEqual(water_row["cost"], 1.0)
        self.assertIsNotNone(total_cost)

    def test_multi_tobacco_rows_use_separate_selected_items(self) -> None:
        _tempdir, db_path = self.make_db()
        water_id = self.save_water(db_path, price=10)
        tobacco_a, tobacco_b = self.first_tobacco_ids(db_path, count=2)
        tobacco_a_packaging = self.default_packaging_id("tobacco", tobacco_a, db_path)
        tobacco_b_packaging = self.default_packaging_id("tobacco", tobacco_b, db_path)
        water_packaging = self.default_packaging_id("distilled_water", water_id, db_path)
        recipe_id = db.save_recipe(
            {"name": "Multi tobacco recipe"},
            [
                {"ingredient_kind": "tobacco", "label": "Virginia", "percent": 12},
                {"ingredient_kind": "tobacco", "label": "Burley", "percent": 18},
                {"ingredient_kind": "distilled_water", "label": "Water", "percent": 70},
            ],
            db_path=db_path,
        )
        selections: dict[int, int] = {}
        tobacco_choices = [tobacco_a_packaging, tobacco_b_packaging]
        for row in db.get_recipe_items(recipe_id, db_path=db_path):
            row_id = int(row["id"])
            if row["ingredient_kind"] == "tobacco":
                selections[row_id] = tobacco_choices.pop(0)
            else:
                selections[row_id] = water_packaging

        rows, total_cost = db.calculate_recipe(recipe_id, 100, selections, db_path=db_path)

        tobacco_rows = [row for row in rows if row["kind"] == "tobacco"]
        self.assertEqual(len(tobacco_rows), 2)
        self.assertNotEqual(tobacco_rows[0]["selected_name"], tobacco_rows[1]["selected_name"])
        self.assertNotEqual(tobacco_rows[0]["cost"], tobacco_rows[1]["cost"])
        self.assertAlmostEqual(total_cost, sum(row["cost"] for row in rows if row["cost"] is not None))

    def test_missing_selection_on_one_recipe_line_makes_total_unknown(self) -> None:
        _tempdir, db_path = self.make_db()
        water_id = self.save_water(db_path)
        tobacco_id = self.first_tobacco_ids(db_path)[0]
        tobacco_packaging_id = self.default_packaging_id("tobacco", tobacco_id, db_path)
        recipe_id = db.save_recipe(
            {"name": "Missing selection recipe"},
            [
                {"ingredient_kind": "tobacco", "label": "Leaf", "percent": 50},
                {"ingredient_kind": "distilled_water", "label": "Water", "percent": 50},
            ],
            db_path=db_path,
        )
        selections = {}
        for row in db.get_recipe_items(recipe_id, db_path=db_path):
            selections[int(row["id"])] = tobacco_packaging_id if row["ingredient_kind"] == "tobacco" else None

        rows, total_cost = db.calculate_recipe(recipe_id, 100, selections, db_path=db_path)

        self.assertIsNone(total_cost)
        water_row = next(row for row in rows if row["kind"] == "distilled_water")
        self.assertEqual(water_row["selected_name"], "Не выбран")
        self.assertIsNone(water_row["cost"])


if __name__ == "__main__":
    unittest.main()
