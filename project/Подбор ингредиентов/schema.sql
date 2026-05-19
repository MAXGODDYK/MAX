PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS glycerin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    grade TEXT,
    concentration TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS tobacco (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    classification TEXT,
    tobacco_type TEXT,
    strength TEXT,
    cut TEXT,
    cut_size_mm TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS gfs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    syrup_type TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS flavors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    flavor_type TEXT,
    taste TEXT,
    carrier TEXT,
    concentration_note TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS propylene_glycol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    grade TEXT,
    concentration TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS distilled_water (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_uah REAL CHECK (price_uah IS NULL OR price_uah >= 0),
    package_amount_g REAL CHECK (package_amount_g IS NULL OR package_amount_g > 0),
    manufacturer TEXT,
    seller TEXT,
    url TEXT,
    phone TEXT,
    telegram TEXT,
    viber TEXT,
    email TEXT,
    grade TEXT,
    concentration TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        length(trim(coalesce(seller, ''))) > 0 OR
        length(trim(coalesce(url, ''))) > 0 OR
        length(trim(coalesce(phone, ''))) > 0 OR
        length(trim(coalesce(telegram, ''))) > 0 OR
        length(trim(coalesce(viber, ''))) > 0 OR
        length(trim(coalesce(email, ''))) > 0
    )
);

CREATE TABLE IF NOT EXISTS item_packagings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_table TEXT NOT NULL CHECK (
        item_table IN ('glycerin', 'tobacco', 'gfs', 'flavors', 'propylene_glycol', 'distilled_water')
    ),
    item_id INTEGER NOT NULL CHECK (item_id > 0),
    label TEXT,
    price_uah REAL NOT NULL CHECK (price_uah >= 0),
    package_amount_g REAL NOT NULL CHECK (package_amount_g > 0),
    url TEXT,
    notes TEXT,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    description TEXT,
    strength_level TEXT,
    smoke_level TEXT,
    heat_resistance TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_items (
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
);

CREATE TABLE IF NOT EXISTS tobacco_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tobacco_strengths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tobacco_cuts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tobacco_classification_map (
    tobacco_id INTEGER NOT NULL REFERENCES tobacco(id) ON DELETE CASCADE,
    classification_id INTEGER NOT NULL REFERENCES tobacco_classifications(id) ON DELETE CASCADE,
    PRIMARY KEY (tobacco_id, classification_id)
);

CREATE INDEX IF NOT EXISTS idx_tobacco_filters ON tobacco(classification, strength, cut, cut_size_mm);
CREATE INDEX IF NOT EXISTS idx_tobacco_classification_map_classification ON tobacco_classification_map(classification_id);
CREATE INDEX IF NOT EXISTS idx_flavors_filters ON flavors(flavor_type, taste);
CREATE INDEX IF NOT EXISTS idx_item_packagings_item ON item_packagings(item_table, item_id);
CREATE INDEX IF NOT EXISTS idx_recipe_items_recipe ON recipe_items(recipe_id);
