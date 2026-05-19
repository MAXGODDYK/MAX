from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "app.py").exists())
sys.path.insert(0, str(APP_DIR))

import database as db  # noqa: E402


class RecipeCatalogTests(unittest.TestCase):
    def make_db(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tempdir = tempfile.TemporaryDirectory()
        db_path = Path(tempdir.name) / "ingredients.db"
        db.init_db(db_path)
        self.addCleanup(tempdir.cleanup)
        return tempdir, db_path

    def test_seed_catalog_has_eight_water_recipes(self) -> None:
        _tempdir, db_path = self.make_db()
        recipes = db.list_recipes(db_path)
        self.assertEqual(len(recipes), 8)

        for recipe in recipes:
            items = db.get_recipe_items(int(recipe["id"]), db_path)
            total = sum(float(item["percent"]) for item in items)
            kinds = [item["ingredient_kind"] for item in items]
            self.assertAlmostEqual(total, 100.0)
            self.assertIn("distilled_water", kinds)

    def test_seed_catalog_contains_multi_tobacco_builds(self) -> None:
        _tempdir, db_path = self.make_db()
        by_name = {recipe["name"]: recipe for recipe in db.list_recipes(db_path)}
        self.assertIn("Баланс Virginia + Burley", by_name)
        self.assertIn("Крепкая Burley + Virginia", by_name)

        balance_items = db.get_recipe_items(int(by_name["Баланс Virginia + Burley"]["id"]), db_path)
        tobacco_labels = [
            item["label"]
            for item in balance_items
            if item["ingredient_kind"] == "tobacco"
        ]
        tobacco_filters = [
            item["tobacco_classification"]
            for item in balance_items
            if item["ingredient_kind"] == "tobacco"
        ]
        self.assertEqual(tobacco_labels, ["Virginia", "Burley"])
        self.assertEqual(tobacco_filters, ["Virginia", "Burley"])

    def test_seed_catalog_has_distilled_water_item_for_costs(self) -> None:
        _tempdir, db_path = self.make_db()
        rows = db.list_items("distilled_water", db_path=db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Дистиллированная вода HELPIX 5 л (ориентир)")
        self.assertEqual(float(rows[0]["price_uah"]), 64.0)
        self.assertEqual(float(rows[0]["package_amount_g"]), 5000.0)


if __name__ == "__main__":
    unittest.main()
