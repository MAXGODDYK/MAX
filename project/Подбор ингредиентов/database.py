from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ingredients.db"
SYNC_TABLE_MARKER = "__table_dirty__"

ITEM_SYNC_COLUMNS = [
    "id",
    "name",
    "price_uah",
    "package_amount_g",
    "manufacturer",
    "seller",
    "url",
    "phone",
    "telegram",
    "viber",
    "email",
]

SYNC_TABLE_COLUMNS: dict[str, list[str]] = {
    "glycerin": [*ITEM_SYNC_COLUMNS, "grade", "concentration", "notes", "created_at", "updated_at"],
    "tobacco": [
        *ITEM_SYNC_COLUMNS,
        "classification",
        "tobacco_type",
        "strength",
        "cut",
        "notes",
        "created_at",
        "updated_at",
        "cut_size_mm",
    ],
    "gfs": [*ITEM_SYNC_COLUMNS, "syrup_type", "notes", "created_at", "updated_at"],
    "flavors": [
        *ITEM_SYNC_COLUMNS,
        "flavor_type",
        "taste",
        "carrier",
        "concentration_note",
        "notes",
        "created_at",
        "updated_at",
    ],
    "propylene_glycol": [*ITEM_SYNC_COLUMNS, "grade", "concentration", "notes", "created_at", "updated_at"],
    "distilled_water": [*ITEM_SYNC_COLUMNS, "grade", "concentration", "notes", "created_at", "updated_at"],
    "item_packagings": [
        "id",
        "item_table",
        "item_id",
        "label",
        "price_uah",
        "package_amount_g",
        "url",
        "notes",
        "is_default",
        "created_at",
        "updated_at",
    ],
    "recipes": [
        "id",
        "name",
        "description",
        "strength_level",
        "smoke_level",
        "heat_resistance",
        "notes",
        "created_at",
        "updated_at",
    ],
    "recipe_items": [
        "id",
        "recipe_id",
        "ingredient_kind",
        "label",
        "percent",
        "tobacco_classification",
        "tobacco_strength",
        "tobacco_cut",
        "tobacco_cut_size_mm",
    ],
    "tobacco_classifications": ["id", "name", "created_at", "updated_at"],
    "tobacco_strengths": ["id", "name", "created_at", "updated_at"],
    "tobacco_cuts": ["id", "name", "created_at", "updated_at"],
    "tobacco_classification_map": ["tobacco_id", "classification_id"],
}

SYNC_TABLES = list(SYNC_TABLE_COLUMNS.keys())
SYNC_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    table: ("id",) for table in SYNC_TABLES if table != "tobacco_classification_map"
}
SYNC_PRIMARY_KEYS["tobacco_classification_map"] = ("tobacco_id", "classification_id")
SYNC_INTEGER_COLUMNS = {
    "id",
    "recipe_id",
    "tobacco_id",
    "classification_id",
    "item_id",
    "is_default",
}
SYNC_NUMBER_COLUMNS = {
    "price_uah",
    "package_amount_g",
    "percent",
}

COMMON_FIELDS = [
    ("name", "Название", "text"),
    ("price_uah", "Цена упаковки, грн", "number"),
    ("package_amount_g", "Вес/объём упаковки, г", "number"),
    ("manufacturer", "Производитель", "text"),
    ("seller", "Продавец", "text"),
    ("url", "Ссылка", "text"),
    ("phone", "Телефон", "text"),
    ("telegram", "Telegram", "text"),
    ("viber", "Viber", "text"),
    ("email", "Email", "text"),
]

ITEM_TABLES: dict[str, dict[str, Any]] = {
    "glycerin": {
        "label": "Глицерин",
        "table": "glycerin",
        "kind": "glycerin",
        "extra_fields": [
            ("grade", "Качество/grade", "text"),
            ("concentration", "Концентрация", "text"),
        ],
        "filter_fields": [],
    },
    "tobacco": {
        "label": "Табак",
        "table": "tobacco",
        "kind": "tobacco",
        "extra_fields": [
            ("classification", "Классификация", "text"),
            ("tobacco_type", "Сорт/тип", "text"),
            ("strength", "Крепость", "text"),
            ("cut", "Нарезка", "text"),
            ("cut_size_mm", "Нарезка, мм", "text"),
        ],
        "filter_fields": [("classification", "Классификация"), ("strength", "Крепость"), ("cut", "Нарезка")],
    },
    "gfs": {
        "label": "ГФС",
        "table": "gfs",
        "kind": "gfs",
        "extra_fields": [("syrup_type", "Тип сиропа", "text")],
        "filter_fields": [("syrup_type", "Тип")],
    },
    "flavors": {
        "label": "Ароматизаторы",
        "table": "flavors",
        "kind": "flavor",
        "extra_fields": [
            ("flavor_type", "Тип", "text"),
            ("taste", "Вкус", "text"),
            ("carrier", "Носитель", "text"),
            ("concentration_note", "Концентрация/заметка", "text"),
        ],
        "filter_fields": [("flavor_type", "Тип"), ("taste", "Вкус")],
    },
    "propylene_glycol": {
        "label": "Пропиленгликоль",
        "table": "propylene_glycol",
        "kind": "propylene_glycol",
        "extra_fields": [
            ("grade", "Качество/grade", "text"),
            ("concentration", "Концентрация", "text"),
        ],
        "filter_fields": [],
    },
    "distilled_water": {
        "label": "Дистиллированная вода",
        "table": "distilled_water",
        "kind": "distilled_water",
        "extra_fields": [
            ("grade", "Качество/grade", "text"),
            ("concentration", "Концентрация", "text"),
        ],
        "filter_fields": [],
    },
}

RECIPE_KIND_LABELS = {
    "tobacco": "Табак",
    "glycerin": "Глицерин",
    "gfs": "ГФС",
    "propylene_glycol": "Пропиленгликоль",
    "flavor": "Ароматизатор",
    "distilled_water": "Дистиллированная вода",
}

KIND_TO_TABLE_KEY = {
    "tobacco": "tobacco",
    "glycerin": "glycerin",
    "gfs": "gfs",
    "propylene_glycol": "propylene_glycol",
    "flavor": "flavors",
    "distilled_water": "distilled_water",
}

DEFAULT_TOBACCO_CLASSIFICATIONS = [
    "Virginia",
    "Burley",
    "Гавана",
    "Золотое Руно",
    "Gold",
    "Махорка",
    "Дюбек",
    "Camel",
    "Winston",
    "Прилуки",
    "Кентуки",
    "Ксанти",
    "Самосад",
    "Міленіум",
    "Давидофф",
    "Капитан Блек",
]

DEFAULT_TOBACCO_STRENGTHS = ["легкая", "средняя", "крепкая", "разная"]
DEFAULT_TOBACCO_CUTS = ["Лапша", "Стрипс", "Хлопья", "Напів-локшина"]

PACKAGING_FIELDS = {"price_uah", "package_amount_g", "url"}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(db_path: Path = DB_PATH):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH, seed_sample: bool = True, seed_references: bool = True) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with session(db_path) as conn:
        conn.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        ensure_item_columns(conn)
        ensure_recipe_items_kind_constraint(conn)
        ensure_recipe_item_columns(conn)
        ensure_sync_tables(conn)
        if seed_references:
            seed_tobacco_reference_data(conn)
        migrate_tobacco_reference_data(conn)
        migrate_item_packagings(conn)
        migrate_recipe_tobacco_filters(conn)
        recipe_count = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        if seed_sample and recipe_count == 0:
            conn.executescript((BASE_DIR / "sample_data.sql").read_text(encoding="utf-8"))
            migrate_tobacco_reference_data(conn)
            migrate_item_packagings(conn)
            migrate_recipe_tobacco_filters(conn)


def init_remote_cache_db(db_path: Path = DB_PATH) -> None:
    init_db(db_path=db_path, seed_sample=False, seed_references=False)


def ensure_sync_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            table_name TEXT NOT NULL,
            row_key TEXT NOT NULL,
            remote_hash TEXT,
            local_hash TEXT,
            pending_op TEXT,
            status TEXT NOT NULL DEFAULT 'synced',
            last_error TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (table_name, row_key)
        )
        """
    )


def sync_row_key(table: str, row: dict[str, Any] | sqlite3.Row) -> str:
    keys = SYNC_PRIMARY_KEYS[table]
    return "|".join(str(row[key]) for key in keys)


def sync_row_key_from_values(table: str, values: dict[str, Any]) -> str | None:
    keys = SYNC_PRIMARY_KEYS[table]
    parts: list[str] = []
    for key in keys:
        value = values.get(key)
        if value is None or str(value).strip() == "":
            return None
        parts.append(str(int(float(value))) if key in SYNC_INTEGER_COLUMNS else str(value))
    return "|".join(parts)


def normalize_sync_value(column: str, value: Any) -> str:
    if value is None:
        return ""
    if column in SYNC_INTEGER_COLUMNS:
        text = str(value).strip()
        return "" if not text else str(int(float(text)))
    if column in SYNC_NUMBER_COLUMNS:
        text = str(value).strip().replace(",", ".")
        if not text:
            return ""
        number = float(text)
        return str(int(number)) if number.is_integer() else f"{number:.12g}"
    return str(value)


def sync_row_hash(table: str, row: dict[str, Any] | sqlite3.Row) -> str:
    payload = {column: normalize_sync_value(column, row[column]) for column in SYNC_TABLE_COLUMNS[table]}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sync_table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    columns = SYNC_TABLE_COLUMNS[table]
    order = ", ".join(SYNC_PRIMARY_KEYS[table])
    rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order}").fetchall()
    return [{column: row[column] for column in columns} for row in rows]


def sync_all_rows(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    return {table: sync_table_rows(conn, table) for table in SYNC_TABLES}


def next_sync_id(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()
    return int(row[0])


def coerce_sync_value(column: str, value: Any) -> Any:
    if value is None or str(value).strip() == "":
        return None
    if column in SYNC_INTEGER_COLUMNS:
        return int(float(str(value).strip()))
    if column in SYNC_NUMBER_COLUMNS:
        return float(str(value).strip().replace(",", "."))
    if column in {"cut_size_mm", "tobacco_cut_size_mm"}:
        return normalize_cut_size_mm(value)
    return str(value)


def sync_clean_import_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for column in SYNC_TABLE_COLUMNS[table]:
        cleaned[column] = coerce_sync_value(column, row.get(column))
    if table == "item_packagings" and cleaned.get("is_default") is None:
        cleaned["is_default"] = 0
    if "created_at" in cleaned and not cleaned["created_at"]:
        cleaned["created_at"] = None
    if "updated_at" in cleaned and not cleaned["updated_at"]:
        cleaned["updated_at"] = None
    return cleaned


def upsert_sync_row(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> None:
    cleaned = sync_clean_import_row(table, row)
    keys = SYNC_PRIMARY_KEYS[table]
    columns = SYNC_TABLE_COLUMNS[table]
    where = " AND ".join(f"{key} = ?" for key in keys)
    key_values = [cleaned[key] for key in keys]
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE {where}", key_values).fetchone()
    if exists:
        update_columns = [
            column
            for column in columns
            if column not in keys and not (column in {"created_at", "updated_at"} and cleaned[column] is None)
        ]
        if update_columns:
            assignments = ", ".join(f"{column} = ?" for column in update_columns)
            conn.execute(
                f"UPDATE {table} SET {assignments} WHERE {where}",
                [cleaned[column] for column in update_columns] + key_values,
            )
        return

    insert_columns = [column for column in columns if cleaned[column] is not None]
    placeholders = ", ".join("?" for _ in insert_columns)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(insert_columns)}) VALUES ({placeholders})",
        [cleaned[column] for column in insert_columns],
    )


def delete_sync_row(conn: sqlite3.Connection, table: str, row_key: str) -> None:
    keys = SYNC_PRIMARY_KEYS[table]
    parts = row_key.split("|")
    values = [int(part) if key in SYNC_INTEGER_COLUMNS else part for key, part in zip(keys, parts)]
    where = " AND ".join(f"{key} = ?" for key in keys)
    conn.execute(f"DELETE FROM {table} WHERE {where}", values)


def mark_sync_pending_conn(conn: sqlite3.Connection, table: str, row_key: str, operation: str) -> None:
    ensure_sync_tables(conn)
    local_hash = None
    if operation != "delete" and row_key != SYNC_TABLE_MARKER:
        rows = {sync_row_key(table, row): row for row in sync_table_rows(conn, table)}
        row = rows.get(row_key)
        local_hash = sync_row_hash(table, row) if row else None
    existing = conn.execute(
        "SELECT remote_hash FROM sync_state WHERE table_name = ? AND row_key = ?",
        (table, row_key),
    ).fetchone()
    remote_hash = existing["remote_hash"] if existing else None
    conn.execute(
        """
        INSERT INTO sync_state
            (table_name, row_key, remote_hash, local_hash, pending_op, status, last_error, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', NULL, CURRENT_TIMESTAMP)
        ON CONFLICT(table_name, row_key) DO UPDATE SET
            local_hash = excluded.local_hash,
            pending_op = excluded.pending_op,
            status = 'pending',
            last_error = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (table, row_key, remote_hash, local_hash, operation),
    )


def mark_sync_pending(table: str, row_key: str, operation: str, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        mark_sync_pending_conn(conn, table, row_key, operation)


def mark_sync_table_dirty_conn(conn: sqlite3.Connection, table: str) -> None:
    mark_sync_pending_conn(conn, table, SYNC_TABLE_MARKER, "table")


def pending_sync_count(db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        ensure_sync_tables(conn)
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM sync_state WHERE pending_op IS NOT NULL OR status = 'conflict'"
            ).fetchone()[0]
        )


def ensure_item_columns(conn: sqlite3.Connection) -> None:
    """Add newly introduced item fields to an existing local database."""
    for table_key, meta in ITEM_TABLES.items():
        table = meta["table"]
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for field, _label, field_type in fields_for(table_key):
            if field not in existing:
                sql_type = "REAL" if field_type == "number" else "TEXT"
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {field} {sql_type}")


def ensure_recipe_items_kind_constraint(conn: sqlite3.Connection) -> None:
    """Rebuild recipe_items when an older CHECK constraint lacks distilled_water."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'recipe_items'"
    ).fetchone()
    if not row or "distilled_water" in (row["sql"] or ""):
        return

    existing_columns = {column["name"] for column in conn.execute("PRAGMA table_info(recipe_items)").fetchall()}
    conn.execute("ALTER TABLE recipe_items RENAME TO recipe_items_old")
    conn.execute(
        """
        CREATE TABLE recipe_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_kind TEXT NOT NULL CHECK (
                ingredient_kind IN ('tobacco', 'glycerin', 'gfs', 'propylene_glycol', 'flavor', 'distilled_water')
            ),
            label TEXT NOT NULL CHECK (length(trim(label)) > 0),
            tobacco_classification TEXT,
            tobacco_strength TEXT,
            tobacco_cut TEXT,
            tobacco_cut_size_mm TEXT,
            percent REAL NOT NULL CHECK (percent >= 0 AND percent <= 100)
        )
        """
    )
    target_columns = [
        "id",
        "recipe_id",
        "ingredient_kind",
        "label",
        "tobacco_classification",
        "tobacco_strength",
        "tobacco_cut",
        "tobacco_cut_size_mm",
        "percent",
    ]
    copy_columns = [column for column in target_columns if column in existing_columns]
    conn.execute(
        f"""
        INSERT INTO recipe_items ({', '.join(copy_columns)})
        SELECT {', '.join(copy_columns)}
        FROM recipe_items_old
        """
    )
    conn.execute("DROP TABLE recipe_items_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recipe_items_recipe ON recipe_items(recipe_id)")


def ensure_recipe_item_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(recipe_items)").fetchall()}
    for column in ["tobacco_classification", "tobacco_strength", "tobacco_cut", "tobacco_cut_size_mm"]:
        if column not in existing:
            conn.execute(f"ALTER TABLE recipe_items ADD COLUMN {column} TEXT")


def item_table_names() -> list[str]:
    return [meta["table"] for meta in ITEM_TABLES.values()]


def table_key_for_item_table(item_table: str) -> str:
    for table_key, meta in ITEM_TABLES.items():
        if meta["table"] == item_table:
            return table_key
    raise ValueError(f"Неизвестная таблица ингредиента: {item_table}")


def format_number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.12g}"


def default_packaging_label(package_amount_g: Any) -> str:
    return f"{format_number(package_amount_g)} г"


def packaging_label(row: dict[str, Any] | sqlite3.Row) -> str:
    return str(row["label"] or "").strip() or default_packaging_label(row["package_amount_g"])


def packaging_display_name(item_name: str, row: dict[str, Any] | sqlite3.Row) -> str:
    price_per_g = float(row["price_uah"]) / float(row["package_amount_g"])
    return (
        f"{item_name} - {packaging_label(row)} / {format_number(row['price_uah'])} грн "
        f"({price_per_g:.2f} грн/г)"
    )


def clean_packaging_values(values: dict[str, Any]) -> dict[str, Any]:
    price = parse_number(values.get("price_uah"))
    package_amount = parse_number(values.get("package_amount_g"))
    if price is None:
        raise ValueError("Цена фасовки обязательна.")
    if price < 0:
        raise ValueError("Цена фасовки не может быть отрицательной.")
    if package_amount is None:
        raise ValueError("Вес/объём фасовки обязателен.")
    if package_amount <= 0:
        raise ValueError("Вес/объём фасовки должен быть больше 0.")
    label = str(values.get("label") or "").strip() or default_packaging_label(package_amount)
    is_default_raw = values.get("is_default")
    is_default = 1 if str(is_default_raw).strip().lower() in {"1", "true", "yes", "да"} else 0
    return {
        "label": label,
        "price_uah": price,
        "package_amount_g": package_amount,
        "url": str(values.get("url") or "").strip() or None,
        "notes": str(values.get("notes") or "").strip() or None,
        "is_default": is_default,
    }


def item_exists_conn(conn: sqlite3.Connection, item_table: str, item_id: int) -> bool:
    if item_table not in item_table_names():
        return False
    row = conn.execute(f"SELECT 1 FROM {item_table} WHERE id = ?", (item_id,)).fetchone()
    return row is not None


def sync_default_packaging_to_item_conn(conn: sqlite3.Connection, item_table: str, item_id: int) -> bool:
    if item_table not in item_table_names():
        return False
    current = conn.execute(
        f"SELECT price_uah, package_amount_g, url FROM {item_table} WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not current:
        return False
    default = conn.execute(
        """
        SELECT price_uah, package_amount_g, url
        FROM item_packagings
        WHERE item_table = ? AND item_id = ?
        ORDER BY is_default DESC, id
        LIMIT 1
        """,
        (item_table, item_id),
    ).fetchone()
    new_price = default["price_uah"] if default else None
    new_package = default["package_amount_g"] if default else None
    new_url = default["url"] if default else None
    changed = (
        normalize_sync_value("price_uah", current["price_uah"]) != normalize_sync_value("price_uah", new_price)
        or normalize_sync_value("package_amount_g", current["package_amount_g"])
        != normalize_sync_value("package_amount_g", new_package)
        or normalize_sync_value("url", current["url"]) != normalize_sync_value("url", new_url)
    )
    if changed:
        conn.execute(
            f"""
            UPDATE {item_table}
            SET price_uah = ?, package_amount_g = ?, url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_price, new_package, new_url, item_id),
        )
    return changed


def repair_item_packagings_conn(conn: sqlite3.Connection) -> set[str]:
    dirty_tables: set[str] = set()
    valid_tables = set(item_table_names())
    for row in conn.execute("SELECT id, item_table, item_id FROM item_packagings").fetchall():
        item_table = str(row["item_table"] or "")
        item_id = int(row["item_id"])
        if item_table not in valid_tables or not item_exists_conn(conn, item_table, item_id):
            conn.execute("DELETE FROM item_packagings WHERE id = ?", (int(row["id"]),))
            dirty_tables.add("item_packagings")

    groups = conn.execute(
        """
        SELECT item_table, item_id
        FROM item_packagings
        GROUP BY item_table, item_id
        """
    ).fetchall()
    for group in groups:
        item_table = str(group["item_table"])
        item_id = int(group["item_id"])
        rows = conn.execute(
            """
            SELECT id, is_default
            FROM item_packagings
            WHERE item_table = ? AND item_id = ?
            ORDER BY is_default DESC, id
            """,
            (item_table, item_id),
        ).fetchall()
        if not rows:
            continue
        chosen_id = int(rows[0]["id"])
        needs_default_fix = any((int(row["id"]) == chosen_id) != bool(row["is_default"]) for row in rows)
        if needs_default_fix:
            conn.execute(
                """
                UPDATE item_packagings
                SET is_default = CASE WHEN id = ? THEN 1 ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_table = ? AND item_id = ?
                """,
                (chosen_id, item_table, item_id),
            )
            dirty_tables.add("item_packagings")
        if sync_default_packaging_to_item_conn(conn, item_table, item_id):
            dirty_tables.add(item_table)
    for item_table in valid_tables:
        rows = conn.execute(f"SELECT id, price_uah, package_amount_g FROM {item_table}").fetchall()
        for row in rows:
            item_id = int(row["id"])
            packaging_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM item_packagings WHERE item_table = ? AND item_id = ?",
                    (item_table, item_id),
                ).fetchone()[0]
            )
            if packaging_count:
                continue
            if row["price_uah"] is not None or row["package_amount_g"] is not None:
                conn.execute(
                    f"""
                    UPDATE {item_table}
                    SET price_uah = NULL, package_amount_g = NULL, url = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (item_id,),
                )
                dirty_tables.add(item_table)
    return dirty_tables


def migrate_item_packagings(conn: sqlite3.Connection) -> None:
    inserted = False
    for meta in ITEM_TABLES.values():
        item_table = meta["table"]
        rows = conn.execute(
            f"""
            SELECT id, price_uah, package_amount_g, url
            FROM {item_table}
            WHERE price_uah IS NOT NULL AND package_amount_g IS NOT NULL
            """
        ).fetchall()
        for row in rows:
            item_id = int(row["id"])
            count = conn.execute(
                "SELECT COUNT(*) FROM item_packagings WHERE item_table = ? AND item_id = ?",
                (item_table, item_id),
            ).fetchone()[0]
            if count:
                continue
            conn.execute(
                """
                INSERT INTO item_packagings (
                    item_table, item_id, label, price_uah, package_amount_g, url, is_default
                )
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    item_table,
                    item_id,
                    default_packaging_label(row["package_amount_g"]),
                    row["price_uah"],
                    row["package_amount_g"],
                    row["url"],
                ),
            )
            inserted = True
    dirty_tables = repair_item_packagings_conn(conn)
    if inserted or dirty_tables:
        mark_sync_table_dirty_conn(conn, "item_packagings")
        for table in dirty_tables:
            if table != "item_packagings":
                mark_sync_table_dirty_conn(conn, table)


def split_reference_text(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).replace(";", ",")
    names: list[str] = []
    for part in text.split(","):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


def normalize_cut_size_mm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    for old, new in {"мм": "", "mm": "", "–": "-", "—": "-", " ": ""}.items():
        text = text.replace(old, new)
    return text.strip() or None


def seed_tobacco_reference_data(conn: sqlite3.Connection) -> None:
    for name in DEFAULT_TOBACCO_CLASSIFICATIONS:
        conn.execute("INSERT OR IGNORE INTO tobacco_classifications (name) VALUES (?)", (name,))
    for name in DEFAULT_TOBACCO_STRENGTHS:
        conn.execute("INSERT OR IGNORE INTO tobacco_strengths (name) VALUES (?)", (name,))
    for name in DEFAULT_TOBACCO_CUTS:
        conn.execute("INSERT OR IGNORE INTO tobacco_cuts (name) VALUES (?)", (name,))


def ensure_tobacco_classification(conn: sqlite3.Connection, name: str) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Название классификации не может быть пустым.")
    conn.execute("INSERT OR IGNORE INTO tobacco_classifications (name) VALUES (?)", (cleaned,))
    row = conn.execute("SELECT id FROM tobacco_classifications WHERE name = ?", (cleaned,)).fetchone()
    return int(row["id"])


def ensure_tobacco_strength(conn: sqlite3.Connection, name: str) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Название крепости не может быть пустым.")
    conn.execute("INSERT OR IGNORE INTO tobacco_strengths (name) VALUES (?)", (cleaned,))
    row = conn.execute("SELECT id FROM tobacco_strengths WHERE name = ?", (cleaned,)).fetchone()
    return int(row["id"])


def ensure_tobacco_cut(conn: sqlite3.Connection, name: str) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Название нарезки не может быть пустым.")
    conn.execute("INSERT OR IGNORE INTO tobacco_cuts (name) VALUES (?)", (cleaned,))
    row = conn.execute("SELECT id FROM tobacco_cuts WHERE name = ?", (cleaned,)).fetchone()
    return int(row["id"])


def classification_names_for_tobacco(conn: sqlite3.Connection, tobacco_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT tc.name
        FROM tobacco_classification_map tcm
        JOIN tobacco_classifications tc ON tc.id = tcm.classification_id
        WHERE tcm.tobacco_id = ?
        ORDER BY tc.name COLLATE NOCASE
        """,
        (tobacco_id,),
    ).fetchall()
    return [row["name"] for row in rows]


def sync_tobacco_classification_cache(conn: sqlite3.Connection, tobacco_id: int) -> None:
    cache = ", ".join(classification_names_for_tobacco(conn, tobacco_id)) or None
    conn.execute(
        "UPDATE tobacco SET classification = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (cache, tobacco_id),
    )


def sync_all_tobacco_classification_cache(conn: sqlite3.Connection) -> None:
    for row in conn.execute("SELECT id FROM tobacco").fetchall():
        sync_tobacco_classification_cache(conn, int(row["id"]))


def set_tobacco_classifications(conn: sqlite3.Connection, tobacco_id: int, names: list[str]) -> None:
    unique_names: list[str] = []
    for name in names:
        cleaned = str(name).strip()
        if cleaned and cleaned not in unique_names:
            unique_names.append(cleaned)
    conn.execute("DELETE FROM tobacco_classification_map WHERE tobacco_id = ?", (tobacco_id,))
    for name in unique_names:
        classification_id = ensure_tobacco_classification(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO tobacco_classification_map (tobacco_id, classification_id) VALUES (?, ?)",
            (tobacco_id, classification_id),
        )
    sync_tobacco_classification_cache(conn, tobacco_id)


def migrate_tobacco_reference_data(conn: sqlite3.Connection) -> None:
    for row in conn.execute("SELECT id, classification, strength, cut FROM tobacco").fetchall():
        tobacco_id = int(row["id"])
        mapped_count = conn.execute(
            "SELECT COUNT(*) FROM tobacco_classification_map WHERE tobacco_id = ?",
            (tobacco_id,),
        ).fetchone()[0]
        if mapped_count == 0 and row["classification"]:
            set_tobacco_classifications(conn, tobacco_id, split_reference_text(row["classification"]))
        elif mapped_count > 0:
            sync_tobacco_classification_cache(conn, tobacco_id)
        if row["strength"] and str(row["strength"]).strip():
            ensure_tobacco_strength(conn, str(row["strength"]).strip())
        if row["cut"] and str(row["cut"]).strip():
            ensure_tobacco_cut(conn, str(row["cut"]).strip())
    split_multi_classification_tobacco_rows(conn)


def migrate_recipe_tobacco_filters(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(recipe_items)").fetchall()}
    if "tobacco_classification" not in existing:
        return
    classifications = {
        str(row["name"]).strip().casefold(): str(row["name"]).strip()
        for row in conn.execute("SELECT name FROM tobacco_classifications").fetchall()
    }
    rows = conn.execute(
        """
        SELECT id, label, tobacco_classification
        FROM recipe_items
        WHERE ingredient_kind = 'tobacco'
        """
    ).fetchall()
    for row in rows:
        if row["tobacco_classification"] and str(row["tobacco_classification"]).strip():
            continue
        label = str(row["label"] or "").strip()
        classification = classifications.get(label.casefold())
        if classification:
            conn.execute(
                "UPDATE recipe_items SET tobacco_classification = ? WHERE id = ?",
                (classification, int(row["id"])),
            )


def build_tobacco_name(classification: str | None, seller: str | None, strength: str | None = None) -> str:
    parts = [part for part in [classification, seller] if part and str(part).strip()]
    name = " - ".join(str(part).strip() for part in parts) or "Табак"
    if strength and str(strength).strip():
        name += f" ({str(strength).strip()})"
    return name


def split_multi_classification_tobacco_rows(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT t.*
        FROM tobacco t
        WHERE (
            SELECT COUNT(*)
            FROM tobacco_classification_map tcm
            WHERE tcm.tobacco_id = t.id
        ) > 1
        """
    ).fetchall()
    copy_fields = [
        "price_uah",
        "package_amount_g",
        "manufacturer",
        "seller",
        "url",
        "phone",
        "telegram",
        "viber",
        "email",
        "tobacco_type",
        "strength",
        "cut",
    ]
    for row in rows:
        original_id = int(row["id"])
        names = classification_names_for_tobacco(conn, original_id)
        original_name = row["name"]
        original_notes = row["notes"] or ""
        for classification in names:
            new_name = build_tobacco_name(classification, row["seller"], row["strength"])
            notes = original_notes
            if original_name and original_name != new_name and "Исходное название объявления:" not in notes:
                notes = (notes + "\n" if notes else "") + f"Исходное название объявления: {original_name}"
            fields = ["name", "classification", *copy_fields, "notes"]
            values = [new_name, classification, *[row[field] for field in copy_fields], notes]
            placeholders = ", ".join("?" for _ in fields)
            cur = conn.execute(
                f"INSERT INTO tobacco ({', '.join(fields)}) VALUES ({placeholders})",
                values,
            )
            new_id = int(cur.lastrowid)
            classification_id = ensure_tobacco_classification(conn, classification)
            conn.execute(
                "INSERT OR IGNORE INTO tobacco_classification_map (tobacco_id, classification_id) VALUES (?, ?)",
                (new_id, classification_id),
            )
        conn.execute("DELETE FROM tobacco WHERE id = ?", (original_id,))


def list_tobacco_classifications(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM tobacco_classifications ORDER BY name COLLATE NOCASE").fetchall()


def list_tobacco_strengths(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM tobacco_strengths ORDER BY name COLLATE NOCASE").fetchall()


def list_tobacco_cuts(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM tobacco_cuts ORDER BY name COLLATE NOCASE").fetchall()


def tobacco_classification_names(db_path: Path = DB_PATH) -> list[str]:
    return [row["name"] for row in list_tobacco_classifications(db_path)]


def tobacco_strength_names(db_path: Path = DB_PATH) -> list[str]:
    return [row["name"] for row in list_tobacco_strengths(db_path)]


def tobacco_cut_names(db_path: Path = DB_PATH) -> list[str]:
    return [row["name"] for row in list_tobacco_cuts(db_path)]


def get_tobacco_classification_names(tobacco_id: int, db_path: Path = DB_PATH) -> list[str]:
    with session(db_path) as conn:
        return classification_names_for_tobacco(conn, tobacco_id)


def add_tobacco_classification(name: str, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        classification_id = ensure_tobacco_classification(conn, name)
        mark_sync_pending_conn(conn, "tobacco_classifications", str(classification_id), "upsert")
        return classification_id


def add_tobacco_strength(name: str, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        strength_id = ensure_tobacco_strength(conn, name)
        mark_sync_pending_conn(conn, "tobacco_strengths", str(strength_id), "upsert")
        return strength_id


def add_tobacco_cut(name: str, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        cut_id = ensure_tobacco_cut(conn, name)
        mark_sync_pending_conn(conn, "tobacco_cuts", str(cut_id), "upsert")
        return cut_id


def rename_tobacco_classification(classification_id: int, new_name: str, db_path: Path = DB_PATH) -> None:
    cleaned = new_name.strip()
    if not cleaned:
        raise ValueError("Название классификации не может быть пустым.")
    with session(db_path) as conn:
        old = conn.execute("SELECT name FROM tobacco_classifications WHERE id = ?", (classification_id,)).fetchone()
        if not old:
            return
        conn.execute(
            "UPDATE tobacco_classifications SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cleaned, classification_id),
        )
        conn.execute(
            "UPDATE recipe_items SET tobacco_classification = ? WHERE tobacco_classification = ?",
            (cleaned, old["name"]),
        )
        sync_all_tobacco_classification_cache(conn)
        mark_sync_pending_conn(conn, "tobacco_classifications", str(classification_id), "upsert")
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def rename_tobacco_strength(strength_id: int, new_name: str, db_path: Path = DB_PATH) -> None:
    cleaned = new_name.strip()
    if not cleaned:
        raise ValueError("Название крепости не может быть пустым.")
    with session(db_path) as conn:
        old = conn.execute("SELECT name FROM tobacco_strengths WHERE id = ?", (strength_id,)).fetchone()
        if not old:
            return
        conn.execute(
            "UPDATE tobacco_strengths SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cleaned, strength_id),
        )
        conn.execute(
            "UPDATE tobacco SET strength = ?, updated_at = CURRENT_TIMESTAMP WHERE strength = ?",
            (cleaned, old["name"]),
        )
        conn.execute(
            "UPDATE recipe_items SET tobacco_strength = ? WHERE tobacco_strength = ?",
            (cleaned, old["name"]),
        )
        mark_sync_pending_conn(conn, "tobacco_strengths", str(strength_id), "upsert")
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def rename_tobacco_cut(cut_id: int, new_name: str, db_path: Path = DB_PATH) -> None:
    cleaned = new_name.strip()
    if not cleaned:
        raise ValueError("Название нарезки не может быть пустым.")
    with session(db_path) as conn:
        old = conn.execute("SELECT name FROM tobacco_cuts WHERE id = ?", (cut_id,)).fetchone()
        if not old:
            return
        conn.execute(
            "UPDATE tobacco_cuts SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cleaned, cut_id),
        )
        conn.execute(
            "UPDATE tobacco SET cut = ?, updated_at = CURRENT_TIMESTAMP WHERE cut = ?",
            (cleaned, old["name"]),
        )
        conn.execute(
            "UPDATE recipe_items SET tobacco_cut = ? WHERE tobacco_cut = ?",
            (cleaned, old["name"]),
        )
        mark_sync_pending_conn(conn, "tobacco_cuts", str(cut_id), "upsert")
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def tobacco_classification_usage(classification_id: int, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        row = conn.execute("SELECT name FROM tobacco_classifications WHERE id = ?", (classification_id,)).fetchone()
        tobacco_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM tobacco_classification_map WHERE classification_id = ?",
                (classification_id,),
            ).fetchone()[0]
        )
        recipe_count = 0
        if row:
            recipe_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM recipe_items WHERE tobacco_classification = ?",
                    (row["name"],),
                ).fetchone()[0]
            )
        return tobacco_count + recipe_count


def tobacco_strength_usage(name: str, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        tobacco_count = int(conn.execute("SELECT COUNT(*) FROM tobacco WHERE strength = ?", (name,)).fetchone()[0])
        recipe_count = int(
            conn.execute("SELECT COUNT(*) FROM recipe_items WHERE tobacco_strength = ?", (name,)).fetchone()[0]
        )
        return tobacco_count + recipe_count


def tobacco_cut_usage(name: str, db_path: Path = DB_PATH) -> int:
    with session(db_path) as conn:
        tobacco_count = int(conn.execute("SELECT COUNT(*) FROM tobacco WHERE cut = ?", (name,)).fetchone()[0])
        recipe_count = int(
            conn.execute("SELECT COUNT(*) FROM recipe_items WHERE tobacco_cut = ?", (name,)).fetchone()[0]
        )
        return tobacco_count + recipe_count


def delete_tobacco_classification(classification_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT name FROM tobacco_classifications WHERE id = ?", (classification_id,)).fetchone()
        if not row:
            return
        mark_sync_pending_conn(conn, "tobacco_classifications", str(classification_id), "delete")
        conn.execute("DELETE FROM tobacco_classifications WHERE id = ?", (classification_id,))
        conn.execute("UPDATE recipe_items SET tobacco_classification = NULL WHERE tobacco_classification = ?", (row["name"],))
        sync_all_tobacco_classification_cache(conn)
        mark_sync_table_dirty_conn(conn, "tobacco_classification_map")
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def delete_tobacco_strength(strength_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT name FROM tobacco_strengths WHERE id = ?", (strength_id,)).fetchone()
        if not row:
            return
        mark_sync_pending_conn(conn, "tobacco_strengths", str(strength_id), "delete")
        conn.execute(
            "UPDATE tobacco SET strength = NULL, updated_at = CURRENT_TIMESTAMP WHERE strength = ?",
            (row["name"],),
        )
        conn.execute("UPDATE recipe_items SET tobacco_strength = NULL WHERE tobacco_strength = ?", (row["name"],))
        conn.execute("DELETE FROM tobacco_strengths WHERE id = ?", (strength_id,))
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def delete_tobacco_cut(cut_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT name FROM tobacco_cuts WHERE id = ?", (cut_id,)).fetchone()
        if not row:
            return
        mark_sync_pending_conn(conn, "tobacco_cuts", str(cut_id), "delete")
        conn.execute(
            "UPDATE tobacco SET cut = NULL, updated_at = CURRENT_TIMESTAMP WHERE cut = ?",
            (row["name"],),
        )
        conn.execute("UPDATE recipe_items SET tobacco_cut = NULL WHERE tobacco_cut = ?", (row["name"],))
        conn.execute("DELETE FROM tobacco_cuts WHERE id = ?", (cut_id,))
        mark_sync_table_dirty_conn(conn, "recipe_items")
        mark_sync_table_dirty_conn(conn, "tobacco")


def fields_for(table_key: str) -> list[tuple[str, str, str]]:
    meta = ITEM_TABLES[table_key]
    return [*COMMON_FIELDS, *meta["extra_fields"], ("notes", "Заметки", "text")]


def form_fields_for(table_key: str) -> list[tuple[str, str, str]]:
    return [field for field in fields_for(table_key) if field[0] not in PACKAGING_FIELDS]


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    return float(text)


def validate_item(values: dict[str, Any]) -> None:
    def filled(value: Any) -> bool:
        return value is not None and str(value).strip() != ""

    if not filled(values.get("name")):
        raise ValueError("Название обязательно.")
    contacts = ["seller", "url", "phone", "telegram", "viber", "email"]
    if not any(filled(values.get(field)) for field in contacts):
        raise ValueError("Нужно заполнить хотя бы один источник: продавец, ссылка, телефон, Telegram, Viber или email.")


def clean_item_values(table_key: str, values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for field, _label, field_type in fields_for(table_key):
        raw = values.get(field)
        if field_type == "number":
            cleaned[field] = parse_number(raw)
        elif field == "cut_size_mm":
            cleaned[field] = normalize_cut_size_mm(raw)
        else:
            cleaned[field] = str(raw or "").strip() or None
    validate_item(cleaned)
    return cleaned


def resolve_tobacco_classification_value(conn: sqlite3.Connection, values: dict[str, Any]) -> str | None:
    raw_ids = values.get("classification_ids")
    if raw_ids is not None:
        if isinstance(raw_ids, str):
            ids = [int(part) for part in raw_ids.replace(";", ",").split(",") if part.strip()]
        else:
            ids = [int(value) for value in raw_ids if str(value).strip()]
        if not ids:
            return None
        if len(ids) > 1:
            raise ValueError("Для одной карточки табака можно выбрать только одну классификацию.")
        placeholders = ", ".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT name FROM tobacco_classifications WHERE id IN ({placeholders}) ORDER BY name COLLATE NOCASE",
            ids,
        ).fetchall()
        return rows[0]["name"] if rows else None

    raw_names = values.get("classification_names")
    if raw_names is not None:
        if isinstance(raw_names, str):
            names = split_reference_text(raw_names)
        else:
            names = [str(value).strip() for value in raw_names if str(value).strip()]
        if len(names) > 1:
            raise ValueError("Для одной карточки табака можно выбрать только одну классификацию.")
        return names[0] if names else None

    names = split_reference_text(values.get("classification"))
    if len(names) > 1:
        raise ValueError("Для одной карточки табака можно выбрать только одну классификацию.")
    return names[0] if names else None


def list_items(
    table_key: str,
    search: str = "",
    filters: dict[str, str] | None = None,
    db_path: Path = DB_PATH,
) -> list[sqlite3.Row]:
    meta = ITEM_TABLES[table_key]
    table = meta["table"]
    where: list[str] = []
    params: list[Any] = []

    if search.strip():
        term = f"%{search.strip()}%"
        columns = [field for field, _label, _type in fields_for(table_key)]
        where.append("(" + " OR ".join(f"coalesce({col}, '') LIKE ?" for col in columns) + ")")
        params.extend([term] * len(columns))

    for field, value in (filters or {}).items():
        if value.strip():
            if table_key == "tobacco" and field == "classification":
                where.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM tobacco_classification_map tcm
                        JOIN tobacco_classifications tc ON tc.id = tcm.classification_id
                        WHERE tcm.tobacco_id = tobacco.id AND tc.name = ?
                    )
                    """
                )
                params.append(value.strip())
            else:
                where.append(f"coalesce({field}, '') = ?")
                params.append(value.strip())

    sql = f"SELECT * FROM {table}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY name COLLATE NOCASE"
    with session(db_path) as conn:
        return conn.execute(sql, params).fetchall()


def distinct_values(table_key: str, field: str, db_path: Path = DB_PATH) -> list[str]:
    if table_key == "tobacco" and field == "classification":
        return tobacco_classification_names(db_path)
    if table_key == "tobacco" and field == "strength":
        return tobacco_strength_names(db_path)
    if table_key == "tobacco" and field == "cut":
        return tobacco_cut_names(db_path)
    table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {field} FROM {table} WHERE {field} IS NOT NULL AND trim({field}) <> '' ORDER BY {field}"
        ).fetchall()
    return [row[0] for row in rows]


def get_item(table_key: str, item_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()


def list_packagings(table_key: str, item_id: int, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    item_table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        return conn.execute(
            """
            SELECT *
            FROM item_packagings
            WHERE item_table = ? AND item_id = ?
            ORDER BY is_default DESC, package_amount_g, id
            """,
            (item_table, item_id),
        ).fetchall()


def get_item_packaging(packaging_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM item_packagings WHERE id = ?", (packaging_id,)).fetchone()


def ensure_default_packaging_from_item_conn(
    conn: sqlite3.Connection,
    item_table: str,
    item_id: int,
    values: dict[str, Any],
) -> None:
    price = values.get("price_uah")
    package_amount = values.get("package_amount_g")
    if price is None or package_amount is None:
        return
    existing = conn.execute(
        """
        SELECT *
        FROM item_packagings
        WHERE item_table = ? AND item_id = ?
        ORDER BY is_default DESC, id
        LIMIT 1
        """,
        (item_table, item_id),
    ).fetchone()
    packaging_values = {
        "price_uah": price,
        "package_amount_g": package_amount,
        "url": values.get("url"),
        "label": existing["label"] if existing and existing["label"] else default_packaging_label(package_amount),
        "notes": existing["notes"] if existing else None,
        "is_default": 1,
    }
    cleaned = clean_packaging_values(packaging_values)
    if existing:
        packaging_id = int(existing["id"])
        conn.execute(
            """
            UPDATE item_packagings
            SET label = ?, price_uah = ?, package_amount_g = ?, url = ?, notes = ?,
                is_default = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                cleaned["label"],
                cleaned["price_uah"],
                cleaned["package_amount_g"],
                cleaned["url"],
                cleaned["notes"],
                packaging_id,
            ),
        )
        conn.execute(
            """
            UPDATE item_packagings
            SET is_default = 0, updated_at = CURRENT_TIMESTAMP
            WHERE item_table = ? AND item_id = ? AND id <> ?
            """,
            (item_table, item_id, packaging_id),
        )
    else:
        cur = conn.execute(
            """
            INSERT INTO item_packagings (
                item_table, item_id, label, price_uah, package_amount_g, url, notes, is_default
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                item_table,
                item_id,
                cleaned["label"],
                cleaned["price_uah"],
                cleaned["package_amount_g"],
                cleaned["url"],
                cleaned["notes"],
            ),
        )
        packaging_id = int(cur.lastrowid)
    mark_sync_pending_conn(conn, "item_packagings", str(packaging_id), "upsert")


def save_item_packaging(
    table_key: str,
    item_id: int,
    values: dict[str, Any],
    packaging_id: int | None = None,
    make_default: bool = False,
    db_path: Path = DB_PATH,
) -> int:
    item_table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        if not item_exists_conn(conn, item_table, item_id):
            raise ValueError("Сначала сохраните карточку товара.")
        cleaned = clean_packaging_values(values)
        existing_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM item_packagings WHERE item_table = ? AND item_id = ?",
                (item_table, item_id),
            ).fetchone()[0]
        )
        if packaging_id is None:
            is_default = 1 if make_default or existing_count == 0 else cleaned["is_default"]
            if is_default:
                conn.execute(
                    """
                    UPDATE item_packagings
                    SET is_default = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE item_table = ? AND item_id = ?
                    """,
                    (item_table, item_id),
                )
            cur = conn.execute(
                """
                INSERT INTO item_packagings (
                    item_table, item_id, label, price_uah, package_amount_g, url, notes, is_default
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_table,
                    item_id,
                    cleaned["label"],
                    cleaned["price_uah"],
                    cleaned["package_amount_g"],
                    cleaned["url"],
                    cleaned["notes"],
                    is_default,
                ),
            )
            saved_id = int(cur.lastrowid)
        else:
            old = conn.execute("SELECT * FROM item_packagings WHERE id = ?", (packaging_id,)).fetchone()
            if not old or old["item_table"] != item_table or int(old["item_id"]) != item_id:
                raise ValueError("Фасовка не найдена для выбранного товара.")
            is_default = 1 if make_default else int(old["is_default"])
            if is_default:
                conn.execute(
                    """
                    UPDATE item_packagings
                    SET is_default = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE item_table = ? AND item_id = ? AND id <> ?
                    """,
                    (item_table, item_id, packaging_id),
                )
            conn.execute(
                """
                UPDATE item_packagings
                SET label = ?, price_uah = ?, package_amount_g = ?, url = ?, notes = ?,
                    is_default = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    cleaned["label"],
                    cleaned["price_uah"],
                    cleaned["package_amount_g"],
                    cleaned["url"],
                    cleaned["notes"],
                    is_default,
                    packaging_id,
                ),
            )
            saved_id = packaging_id

        dirty_tables = repair_item_packagings_conn(conn)
        mark_sync_pending_conn(conn, "item_packagings", str(saved_id), "upsert")
        if make_default or cleaned["is_default"] or "item_packagings" in dirty_tables:
            mark_sync_table_dirty_conn(conn, "item_packagings")
        for table in dirty_tables:
            if table != "item_packagings":
                mark_sync_table_dirty_conn(conn, table)
        return saved_id


def delete_item_packaging(packaging_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM item_packagings WHERE id = ?", (packaging_id,)).fetchone()
        if not row:
            return
        mark_sync_pending_conn(conn, "item_packagings", str(packaging_id), "delete")
        conn.execute("DELETE FROM item_packagings WHERE id = ?", (packaging_id,))
        dirty_tables = repair_item_packagings_conn(conn)
        item_table = str(row["item_table"])
        item_id = int(row["item_id"])
        if sync_default_packaging_to_item_conn(conn, item_table, item_id):
            dirty_tables.add(item_table)
        for table in dirty_tables:
            mark_sync_table_dirty_conn(conn, table)


def set_default_packaging(packaging_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM item_packagings WHERE id = ?", (packaging_id,)).fetchone()
        if not row:
            return
        item_table = str(row["item_table"])
        item_id = int(row["item_id"])
        conn.execute(
            """
            UPDATE item_packagings
            SET is_default = CASE WHEN id = ? THEN 1 ELSE 0 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE item_table = ? AND item_id = ?
            """,
            (packaging_id, item_table, item_id),
        )
        dirty_tables = repair_item_packagings_conn(conn)
        mark_sync_table_dirty_conn(conn, "item_packagings")
        if sync_default_packaging_to_item_conn(conn, item_table, item_id):
            dirty_tables.add(item_table)
        for table in dirty_tables:
            if table != "item_packagings":
                mark_sync_table_dirty_conn(conn, table)


def save_item(table_key: str, values: dict[str, Any], item_id: int | None = None, db_path: Path = DB_PATH) -> int:
    table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        values = dict(values)
        provided_fields = set(values)
        if item_id is not None:
            existing = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
            if existing:
                for field, _label, _type in fields_for(table_key):
                    values.setdefault(field, existing[field])
        classification_name: str | None = None
        if table_key == "tobacco":
            classification_name = resolve_tobacco_classification_value(conn, values)
            values["classification"] = classification_name or ""
            strength = str(values.get("strength") or "").strip()
            if strength:
                ensure_tobacco_strength(conn, strength)
            cut = str(values.get("cut") or "").strip()
            if cut:
                ensure_tobacco_cut(conn, cut)
        cleaned = clean_item_values(table_key, values)
        fields = list(cleaned.keys())
        if item_id is None:
            placeholders = ", ".join("?" for _ in fields)
            sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})"
            cur = conn.execute(sql, [cleaned[field] for field in fields])
            saved_id = int(cur.lastrowid)
        else:
            assignments = ", ".join(f"{field} = ?" for field in fields)
            sql = f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            conn.execute(sql, [cleaned[field] for field in fields] + [item_id])
            saved_id = item_id
        if table_key == "tobacco":
            set_tobacco_classifications(conn, saved_id, [classification_name] if classification_name else [])
            mark_sync_table_dirty_conn(conn, "tobacco_classification_map")
        if {"price_uah", "package_amount_g"}.issubset(provided_fields):
            ensure_default_packaging_from_item_conn(conn, table, saved_id, cleaned)
        mark_sync_pending_conn(conn, table, str(saved_id), "upsert")
        return saved_id


def delete_item(table_key: str, item_id: int, db_path: Path = DB_PATH) -> None:
    table = ITEM_TABLES[table_key]["table"]
    with session(db_path) as conn:
        for row in conn.execute(
            "SELECT id FROM item_packagings WHERE item_table = ? AND item_id = ?",
            (table, item_id),
        ).fetchall():
            mark_sync_pending_conn(conn, "item_packagings", str(row["id"]), "delete")
        conn.execute("DELETE FROM item_packagings WHERE item_table = ? AND item_id = ?", (table, item_id))
        mark_sync_pending_conn(conn, table, str(item_id), "delete")
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        if table_key == "tobacco":
            mark_sync_table_dirty_conn(conn, "tobacco_classification_map")


def list_recipes(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM recipes ORDER BY name COLLATE NOCASE").fetchall()


def get_recipe(recipe_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    with session(db_path) as conn:
        return conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()


def get_recipe_items(recipe_id: int, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return conn.execute(
            "SELECT * FROM recipe_items WHERE recipe_id = ? ORDER BY id",
            (recipe_id,),
        ).fetchall()


def save_recipe(
    values: dict[str, str],
    items: list[dict[str, Any]],
    recipe_id: int | None = None,
    db_path: Path = DB_PATH,
) -> int:
    name = values.get("name", "").strip()
    if not name:
        raise ValueError("Название рецепта обязательно.")
    if not items:
        raise ValueError("Добавьте хотя бы один ингредиент рецепта.")
    total = sum(parse_number(item.get("percent")) or 0 for item in items)
    if round(total, 4) != 100:
        raise ValueError(f"Сумма процентов должна быть 100. Сейчас: {total:g}.")

    recipe_fields = ["name", "description", "strength_level", "smoke_level", "heat_resistance", "notes"]
    cleaned = {field: str(values.get(field, "")).strip() or None for field in recipe_fields}

    with session(db_path) as conn:
        classification_by_name = {
            str(row["name"]).strip().casefold(): str(row["name"]).strip()
            for row in conn.execute("SELECT name FROM tobacco_classifications").fetchall()
        }
        if recipe_id is None:
            placeholders = ", ".join("?" for _ in recipe_fields)
            cur = conn.execute(
                f"INSERT INTO recipes ({', '.join(recipe_fields)}) VALUES ({placeholders})",
                [cleaned[field] for field in recipe_fields],
            )
            recipe_id = int(cur.lastrowid)
        else:
            assignments = ", ".join(f"{field} = ?" for field in recipe_fields)
            conn.execute(
                f"UPDATE recipes SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [cleaned[field] for field in recipe_fields] + [recipe_id],
            )
            conn.execute("DELETE FROM recipe_items WHERE recipe_id = ?", (recipe_id,))

        for item in items:
            kind = str(item.get("ingredient_kind", "")).strip()
            if kind not in RECIPE_KIND_LABELS:
                raise ValueError(f"Неизвестный тип ингредиента: {kind}")
            tobacco_classification = None
            tobacco_strength = None
            tobacco_cut = None
            tobacco_cut_size_mm = None
            label_input = str(item.get("label", "")).strip()
            if kind == "tobacco":
                tobacco_classification = str(item.get("tobacco_classification") or "").strip() or None
                if not tobacco_classification and label_input:
                    tobacco_classification = classification_by_name.get(label_input.casefold())
                if tobacco_classification:
                    ensure_tobacco_classification(conn, tobacco_classification)
                tobacco_strength = str(item.get("tobacco_strength") or "").strip() or None
                if tobacco_strength:
                    ensure_tobacco_strength(conn, tobacco_strength)
                tobacco_cut = str(item.get("tobacco_cut") or "").strip() or None
                if tobacco_cut:
                    ensure_tobacco_cut(conn, tobacco_cut)
                tobacco_cut_size_mm = normalize_cut_size_mm(item.get("tobacco_cut_size_mm"))
            label = label_input or tobacco_classification or RECIPE_KIND_LABELS.get(kind, kind)
            percent = parse_number(item.get("percent"))
            if percent is None or percent < 0:
                raise ValueError("Процент ингредиента должен быть числом не меньше 0.")
            conn.execute(
                """
                INSERT INTO recipe_items (
                    recipe_id,
                    ingredient_kind,
                    label,
                    tobacco_classification,
                    tobacco_strength,
                    tobacco_cut,
                    tobacco_cut_size_mm,
                    percent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    kind,
                    label,
                    tobacco_classification,
                    tobacco_strength,
                    tobacco_cut,
                    tobacco_cut_size_mm,
                    percent,
                ),
            )
        mark_sync_pending_conn(conn, "recipes", str(recipe_id), "upsert")
        mark_sync_table_dirty_conn(conn, "recipe_items")
    return recipe_id


def delete_recipe(recipe_id: int, db_path: Path = DB_PATH) -> None:
    with session(db_path) as conn:
        mark_sync_pending_conn(conn, "recipes", str(recipe_id), "delete")
        conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        mark_sync_table_dirty_conn(conn, "recipe_items")


def item_options_for_kind(kind: str, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    table_key = KIND_TO_TABLE_KEY[kind]
    return list_items(table_key, db_path=db_path)


def item_options_for_recipe_item(recipe_item: sqlite3.Row | dict[str, Any], db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    kind = recipe_item["ingredient_kind"]
    table_key = KIND_TO_TABLE_KEY[kind]
    if kind != "tobacco":
        return list_items(table_key, db_path=db_path)

    filters: dict[str, str] = {}
    for recipe_field, item_field in [
        ("tobacco_classification", "classification"),
        ("tobacco_strength", "strength"),
        ("tobacco_cut", "cut"),
    ]:
        value = recipe_item[recipe_field] if recipe_field in recipe_item.keys() else None
        if value and str(value).strip():
            filters[item_field] = str(value).strip()

    cut_size = recipe_item["tobacco_cut_size_mm"] if "tobacco_cut_size_mm" in recipe_item.keys() else None
    normalized_cut_size = normalize_cut_size_mm(cut_size)
    if normalized_cut_size:
        filters["cut_size_mm"] = normalized_cut_size

    return list_items("tobacco", filters=filters, db_path=db_path)


def packaging_options_for_recipe_item(
    recipe_item: sqlite3.Row | dict[str, Any],
    db_path: Path = DB_PATH,
) -> list[sqlite3.Row]:
    kind = recipe_item["ingredient_kind"]
    table_key = KIND_TO_TABLE_KEY[kind]
    item_table = ITEM_TABLES[table_key]["table"]
    items = item_options_for_recipe_item(recipe_item, db_path=db_path)
    item_ids = [int(row["id"]) for row in items]
    if not item_ids:
        return []
    placeholders = ", ".join("?" for _ in item_ids)
    with session(db_path) as conn:
        return conn.execute(
            f"""
            SELECT
                p.id AS packaging_id,
                p.item_table,
                p.item_id,
                p.label AS packaging_label,
                p.price_uah,
                p.package_amount_g,
                p.url AS packaging_url,
                p.notes AS packaging_notes,
                p.is_default,
                i.name AS item_name,
                i.seller AS seller
            FROM item_packagings p
            JOIN {item_table} i ON i.id = p.item_id
            WHERE p.item_table = ? AND p.item_id IN ({placeholders})
            ORDER BY i.name COLLATE NOCASE, p.is_default DESC, p.package_amount_g, p.id
            """,
            [item_table, *item_ids],
        ).fetchall()


def calculate_recipe(
    recipe_id: int,
    total_weight_g: float,
    selections: dict[object, int | None],
    db_path: Path = DB_PATH,
) -> tuple[list[dict[str, Any]], float | None]:
    if total_weight_g <= 0:
        raise ValueError("Общий вес должен быть больше 0.")

    rows: list[dict[str, Any]] = []
    total_cost = 0.0
    has_unknown = False

    for recipe_item in get_recipe_items(recipe_id, db_path=db_path):
        kind = recipe_item["ingredient_kind"]
        grams = total_weight_g * float(recipe_item["percent"]) / 100
        recipe_item_id = int(recipe_item["id"])
        if recipe_item_id in selections:
            item_id = selections.get(recipe_item_id)
        elif str(recipe_item_id) in selections:
            item_id = selections.get(str(recipe_item_id))
        else:
            item_id = selections.get(kind)
        selected_name = "Не выбран"
        price_per_g = None
        cost = None

        if item_id:
            table_key = KIND_TO_TABLE_KEY[kind]
            item_table = ITEM_TABLES[table_key]["table"]
            packaging = get_item_packaging(int(item_id), db_path=db_path)
            if packaging and packaging["item_table"] == item_table:
                item = get_item(table_key, int(packaging["item_id"]), db_path=db_path)
                if item:
                    selected_name = packaging_display_name(item["name"], packaging)
                    price_per_g = float(packaging["price_uah"]) / float(packaging["package_amount_g"])
                    cost = price_per_g * grams
                    total_cost += cost
                else:
                    has_unknown = True
            else:
                has_unknown = True
        else:
            has_unknown = True

        rows.append(
            {
                "recipe_item_id": recipe_item_id,
                "kind": kind,
                "label": recipe_item["label"],
                "percent": float(recipe_item["percent"]),
                "grams": grams,
                "selected_name": selected_name,
                "selected_packaging_id": item_id,
                "price_per_g": price_per_g,
                "cost": cost,
            }
        )

    return rows, None if has_unknown else total_cost
