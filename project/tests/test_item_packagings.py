from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists())
sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402


class ItemPackagingTests(unittest.TestCase):
    def make_db(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tempdir = tempfile.TemporaryDirectory()
        db_path = Path(tempdir.name) / "ingredients.db"
        db.init_db(db_path)
        self.addCleanup(tempdir.cleanup)
        return tempdir, db_path

    def test_init_db_migrates_existing_prices_to_packagings(self) -> None:
        _tempdir, db_path = self.make_db()
        with db.session(db_path) as conn:
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'item_packagings'"
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) FROM item_packagings").fetchone()[0]
        self.assertIsNotNone(table)
        self.assertIn("item_packagings", db.SYNC_TABLES)
        self.assertGreater(count, 0)

    def test_save_item_creates_default_packaging_for_old_imports(self) -> None:
        _tempdir, db_path = self.make_db()
        item_id = db.save_item(
            "flavors",
            {
                "name": "Cherry aroma",
                "price_uah": 92,
                "package_amount_g": 10,
                "seller": "Test seller",
                "flavor_type": "Кальянні ароматизатори",
                "taste": "Вишня",
            },
            db_path=db_path,
        )
        packagings = db.list_packagings("flavors", item_id, db_path=db_path)
        self.assertEqual(len(packagings), 1)
        self.assertEqual(float(packagings[0]["price_uah"]), 92.0)
        self.assertEqual(float(packagings[0]["package_amount_g"]), 10.0)
        self.assertEqual(int(packagings[0]["is_default"]), 1)

    def test_packaging_crud_and_default_mirror(self) -> None:
        _tempdir, db_path = self.make_db()
        item_id = db.save_item(
            "flavors",
            {
                "name": "Mint aroma",
                "seller": "Test seller",
                "flavor_type": "food",
                "taste": "mint",
            },
            db_path=db_path,
        )
        first = db.save_item_packaging(
            "flavors",
            item_id,
            {"package_amount_g": 100, "price_uah": 175, "url": "https://example.test/100"},
            db_path=db_path,
        )
        second = db.save_item_packaging(
            "flavors",
            item_id,
            {"package_amount_g": 250, "price_uah": 350, "url": "https://example.test/250"},
            db_path=db_path,
        )
        item = db.get_item("flavors", item_id, db_path=db_path)
        self.assertEqual(float(item["price_uah"]), 175.0)
        self.assertEqual(float(item["package_amount_g"]), 100.0)

        db.set_default_packaging(second, db_path=db_path)
        item = db.get_item("flavors", item_id, db_path=db_path)
        self.assertEqual(float(item["price_uah"]), 350.0)
        self.assertEqual(float(item["package_amount_g"]), 250.0)
        self.assertEqual(item["url"], "https://example.test/250")

        db.save_item_packaging(
            "flavors",
            item_id,
            {"package_amount_g": 250, "price_uah": 325, "url": "https://example.test/250-new"},
            packaging_id=second,
            db_path=db_path,
        )
        item = db.get_item("flavors", item_id, db_path=db_path)
        self.assertEqual(float(item["price_uah"]), 325.0)

        db.delete_item_packaging(second, db_path=db_path)
        packagings = db.list_packagings("flavors", item_id, db_path=db_path)
        self.assertEqual([int(row["id"]) for row in packagings], [first])
        self.assertEqual(int(packagings[0]["is_default"]), 1)
        item = db.get_item("flavors", item_id, db_path=db_path)
        self.assertEqual(float(item["package_amount_g"]), 100.0)

    def test_calculator_uses_selected_packaging_price(self) -> None:
        _tempdir, db_path = self.make_db()
        item_id = db.save_item(
            "flavors",
            {
                "name": "Grape aroma",
                "seller": "Test seller",
                "flavor_type": "food",
                "taste": "grape",
            },
            db_path=db_path,
        )
        cheap = db.save_item_packaging(
            "flavors",
            item_id,
            {"package_amount_g": 250, "price_uah": 250},
            db_path=db_path,
        )
        expensive = db.save_item_packaging(
            "flavors",
            item_id,
            {"package_amount_g": 10, "price_uah": 100},
            db_path=db_path,
        )
        recipe_id = db.save_recipe(
            {"name": "Flavor only"},
            [{"ingredient_kind": "flavor", "label": "Aroma", "percent": 100}],
            db_path=db_path,
        )
        recipe_item_id = int(db.get_recipe_items(recipe_id, db_path=db_path)[0]["id"])

        _rows, cheap_total = db.calculate_recipe(recipe_id, 10, {recipe_item_id: cheap}, db_path=db_path)
        rows, expensive_total = db.calculate_recipe(recipe_id, 10, {recipe_item_id: expensive}, db_path=db_path)

        self.assertAlmostEqual(cheap_total, 10.0)
        self.assertAlmostEqual(expensive_total, 100.0)
        self.assertIn("10 г", rows[0]["selected_name"])

    def test_item_without_packaging_makes_total_unknown(self) -> None:
        _tempdir, db_path = self.make_db()
        item_id = db.save_item(
            "flavors",
            {
                "name": "No price aroma",
                "seller": "Test seller",
                "flavor_type": "food",
                "taste": "plain",
            },
            db_path=db_path,
        )
        with db.session(db_path) as conn:
            conn.execute("DELETE FROM item_packagings WHERE item_table = 'flavors'")
            conn.execute("UPDATE flavors SET price_uah = NULL, package_amount_g = NULL, url = NULL")
        recipe_id = db.save_recipe(
            {"name": "Unknown package"},
            [{"ingredient_kind": "flavor", "label": "Aroma", "percent": 100}],
            db_path=db_path,
        )
        item = db.get_recipe_items(recipe_id, db_path=db_path)[0]
        self.assertEqual(db.packaging_options_for_recipe_item(item, db_path=db_path), [])
        _rows, total = db.calculate_recipe(recipe_id, 10, {int(item["id"]): item_id}, db_path=db_path)
        self.assertIsNone(total)


if __name__ == "__main__":
    unittest.main()
