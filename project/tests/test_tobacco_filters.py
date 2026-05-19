from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists())
sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402


class TobaccoFilterTests(unittest.TestCase):
    def make_db(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tempdir = tempfile.TemporaryDirectory()
        db_path = Path(tempdir.name) / "ingredients.db"
        db.init_db(db_path)
        self.addCleanup(tempdir.cleanup)
        return tempdir, db_path

    def save_tobacco(
        self,
        db_path: Path,
        name: str,
        classification: str,
        strength: str,
        cut: str,
        cut_size_mm: str = "",
    ) -> int:
        return db.save_item(
            "tobacco",
            {
                "name": name,
                "price_uah": 100,
                "package_amount_g": 100,
                "seller": "Test seller",
                "classification": classification,
                "tobacco_type": "test",
                "strength": strength,
                "cut": cut,
                "cut_size_mm": cut_size_mm,
            },
            db_path=db_path,
        )

    def test_schema_has_cut_reference_and_recipe_filter_columns(self) -> None:
        _tempdir, db_path = self.make_db()
        with db.session(db_path) as conn:
            tobacco_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tobacco)").fetchall()}
            recipe_columns = {row["name"] for row in conn.execute("PRAGMA table_info(recipe_items)").fetchall()}
            cut_table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tobacco_cuts'"
            ).fetchone()
        self.assertIn("cut_size_mm", tobacco_columns)
        self.assertIn("tobacco_classification", recipe_columns)
        self.assertIn("tobacco_strength", recipe_columns)
        self.assertIn("tobacco_cut", recipe_columns)
        self.assertIn("tobacco_cut_size_mm", recipe_columns)
        self.assertIsNotNone(cut_table)
        self.assertIn("tobacco_cuts", db.SYNC_TABLES)

    def test_cut_reference_is_seeded_from_current_tobacco_rows(self) -> None:
        _tempdir, db_path = self.make_db()
        cuts = db.tobacco_cut_names(db_path)
        self.assertIn("Лапша", cuts)
        self.assertIn("Стрипс", cuts)

    def test_save_recipe_stores_tobacco_filters_and_normalizes_mm(self) -> None:
        _tempdir, db_path = self.make_db()
        recipe_id = db.save_recipe(
            {"name": "Filtered tobacco recipe"},
            [
                {
                    "ingredient_kind": "tobacco",
                    "label": "Virginia",
                    "tobacco_classification": "Virginia",
                    "tobacco_strength": "средняя",
                    "tobacco_cut": "Лапша",
                    "tobacco_cut_size_mm": "20 - 40 мм",
                    "percent": 100,
                }
            ],
            db_path=db_path,
        )
        item = db.get_recipe_items(recipe_id, db_path=db_path)[0]
        self.assertEqual(item["tobacco_classification"], "Virginia")
        self.assertEqual(item["tobacco_strength"], "средняя")
        self.assertEqual(item["tobacco_cut"], "Лапша")
        self.assertEqual(item["tobacco_cut_size_mm"], "20-40")

    def test_recipe_item_options_filter_tobacco_by_all_filled_fields(self) -> None:
        _tempdir, db_path = self.make_db()
        wanted = self.save_tobacco(db_path, "Wanted Virginia", "Virginia", "средняя", "Лапша", "20-40")
        self.save_tobacco(db_path, "Wrong class Burley", "Burley", "средняя", "Лапша", "20-40")
        self.save_tobacco(db_path, "Wrong strength Virginia", "Virginia", "крепкая", "Лапша", "20-40")
        self.save_tobacco(db_path, "Wrong cut Virginia", "Virginia", "средняя", "Стрипс", "20-40")
        self.save_tobacco(db_path, "Wrong mm Virginia", "Virginia", "средняя", "Лапша", "10-20")
        recipe_id = db.save_recipe(
            {"name": "Strict tobacco filter"},
            [
                {
                    "ingredient_kind": "tobacco",
                    "label": "Virginia",
                    "tobacco_classification": "Virginia",
                    "tobacco_strength": "средняя",
                    "tobacco_cut": "Лапша",
                    "tobacco_cut_size_mm": "20-40",
                    "percent": 100,
                }
            ],
            db_path=db_path,
        )
        item = db.get_recipe_items(recipe_id, db_path=db_path)[0]
        option_ids = [int(row["id"]) for row in db.item_options_for_recipe_item(item, db_path=db_path)]
        self.assertEqual(option_ids, [wanted])

    def test_empty_recipe_mm_does_not_filter_tobacco_by_mm(self) -> None:
        _tempdir, db_path = self.make_db()
        first = self.save_tobacco(db_path, "Virginia 20-40", "Virginia", "средняя", "Лапша", "20-40")
        second = self.save_tobacco(db_path, "Virginia 10-20", "Virginia", "средняя", "Лапша", "10-20")
        recipe_id = db.save_recipe(
            {"name": "No mm filter"},
            [
                {
                    "ingredient_kind": "tobacco",
                    "label": "Virginia",
                    "tobacco_classification": "Virginia",
                    "tobacco_strength": "средняя",
                    "tobacco_cut": "Лапша",
                    "tobacco_cut_size_mm": "",
                    "percent": 100,
                }
            ],
            db_path=db_path,
        )
        item = db.get_recipe_items(recipe_id, db_path=db_path)[0]
        option_ids = [int(row["id"]) for row in db.item_options_for_recipe_item(item, db_path=db_path)]
        self.assertIn(first, option_ids)
        self.assertIn(second, option_ids)


if __name__ == "__main__":
    unittest.main()
