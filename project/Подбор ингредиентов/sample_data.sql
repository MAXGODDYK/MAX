INSERT INTO glycerin
    (name, price_uah, package_amount_g, manufacturer, seller, grade, concentration, notes)
VALUES
    ('Демо глицерин пищевой 99.5%', 220, 1000, 'Demo FoodChem', 'Демо-продавец', 'пищевой', '99.5%', 'Пример записи. Проверь реальный сертификат и назначение перед покупкой.'),
    ('Демо глицерин фарм-grade', NULL, 500, 'Demo Pharma', 'Демо-продавец', 'фармацевтический', '99.7%', 'Цена не задана: калькулятор покажет неизвестную стоимость.');

INSERT INTO tobacco
    (name, price_uah, package_amount_g, manufacturer, seller, classification, tobacco_type, strength, cut, notes)
VALUES
    ('Демо Virginia светлая', 180, 250, 'Demo Leaf', 'Демо-продавец', 'Virginia', 'листовой резаный', 'легкая', 'Лапша', 'Сушеный и нарезанный табак для тестовых расчётов.'),
    ('Демо Burley тёмная', 260, 250, 'Demo Leaf', 'Демо-продавец', 'Burley', 'листовой резаный', 'крепкая', 'Лапша', 'Более плотный профиль для крепких рецептов.');

INSERT INTO gfs
    (name, price_uah, package_amount_g, manufacturer, seller, syrup_type, notes)
VALUES
    ('Демо ГФС 42', 95, 1000, 'Demo Syrup', 'Демо-продавец', 'ГФС-42', 'Пример сиропа. Для реального использования проверяй пищевое качество.'),
    ('Демо инвертный сироп', NULL, 1000, 'Demo Syrup', 'Демо-продавец', 'инвертный/аналог', 'Альтернативная запись без цены.');

INSERT INTO flavors
    (name, price_uah, package_amount_g, manufacturer, seller, flavor_type, taste, carrier, concentration_note, notes)
VALUES
    ('Демо ароматизатор яблоко', 140, 100, 'Demo Aroma', 'Демо-продавец', 'пищевой водорастворимый', 'яблоко', 'PG/вода', 'обычно тестируют малыми дозами', 'Не использовать масляные ароматизаторы.'),
    ('Демо ароматизатор мята', 150, 100, 'Demo Aroma', 'Демо-продавец', 'пищевой водорастворимый', 'мята', 'PG', 'яркий вкус, начинать осторожно', 'Не медицинская рекомендация.');

INSERT INTO propylene_glycol
    (name, price_uah, package_amount_g, manufacturer, seller, grade, concentration, notes)
VALUES
    ('Демо пропиленгликоль пищевой', 190, 1000, 'Demo FoodChem', 'Демо-продавец', 'пищевой', '99.8%', 'Пример записи. Проверяй назначение и документы.'),
    ('Демо пропиленгликоль фарм-grade', NULL, 500, 'Demo Pharma', 'Демо-продавец', 'фармацевтический', '99.9%', 'Цена не задана.');

INSERT INTO distilled_water
    (name, price_uah, package_amount_g, manufacturer, seller, url, grade, concentration, notes)
VALUES
    ('Дистиллированная вода HELPIX 5 л (ориентир)', 64, 5000, 'HELPIX', 'ARS.ua', 'https://ars.ua/voda-distilovana-helpix-4823075800193-b-ja-5-l.html', 'дистиллированная', '5 л', 'Ориентировочная цена и фасовка для расчёта. Назначение авто/бытовое; перед использованием проверить подходящее качество, состав и актуальную цену.');

INSERT INTO recipes
    (name, description, strength_level, smoke_level, heat_resistance, notes)
VALUES
    ('Лёгкая дымная', 'Мягкая смесь с высоким выходом пара и умеренным вкусом.', 'низкая', 'высокая', 'средняя', 'Подходит для первых тестов малыми партиями. Вода добавлена малой долей для корректировки вязкости.'),
    ('Средняя сбалансированная', 'Баланс крепости, дымности и стабильного прогрева.', 'средняя', 'высокая', 'выше средней', 'Базовая рабочая формула для сравнения ингредиентов с малой долей воды.'),
    ('Крепкая жаростойкая', 'Больше табака и плотнее сиропная часть для устойчивости к жару.', 'высокая', 'средняя', 'высокая', 'Требует аккуратного прогрева и теста на небольшой партии. Вода не должна делать смесь жидкой.'),
    ('Лёгкая Virginia Gold', 'Мягкая светлая сборка с Virginia Gold как основной табачной базой.', 'низкая', 'очень высокая', 'средняя', 'Для лёгкого профиля и плотного дыма без высокой крепости.'),
    ('Мягкая Virginia дымная', 'Сборка на Virginia средней крепости с акцентом на дымность.', 'ниже средней', 'очень высокая', 'средняя', 'Хорошая база для сравнения разных Virginia.'),
    ('Баланс Virginia + Burley', 'Смешанная табачная база: Virginia даёт мягкость, Burley добавляет плотность.', 'средняя', 'высокая', 'выше средней', 'В калькуляторе выбери отдельные товары для строк Virginia и Burley.'),
    ('Крепкая Burley + Virginia', 'Крепкая сборка с Burley как главным листом и Virginia для смягчения.', 'высокая', 'средняя', 'высокая', 'Тестировать малыми партиями и не перегревать.'),
    ('Жаростойкая Burley', 'Плотная сборка на Burley для высокой жаростойкости.', 'высокая', 'средняя', 'очень высокая', 'Самая плотная сборка: начинать с меньшего жара и короткого теста.');

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Табак', 22 FROM recipes WHERE name = 'Лёгкая дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 36 FROM recipes WHERE name = 'Лёгкая дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 26 FROM recipes WHERE name = 'Лёгкая дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 6 FROM recipes WHERE name = 'Лёгкая дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Лёгкая дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 7 FROM recipes WHERE name = 'Лёгкая дымная';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Табак', 30 FROM recipes WHERE name = 'Средняя сбалансированная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 32 FROM recipes WHERE name = 'Средняя сбалансированная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 24 FROM recipes WHERE name = 'Средняя сбалансированная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 5 FROM recipes WHERE name = 'Средняя сбалансированная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Средняя сбалансированная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 6 FROM recipes WHERE name = 'Средняя сбалансированная';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Табак', 38 FROM recipes WHERE name = 'Крепкая жаростойкая';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 28 FROM recipes WHERE name = 'Крепкая жаростойкая';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 23 FROM recipes WHERE name = 'Крепкая жаростойкая';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 3 FROM recipes WHERE name = 'Крепкая жаростойкая';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Крепкая жаростойкая';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 5 FROM recipes WHERE name = 'Крепкая жаростойкая';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Virginia Gold', 20 FROM recipes WHERE name = 'Лёгкая Virginia Gold';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 38 FROM recipes WHERE name = 'Лёгкая Virginia Gold';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 27 FROM recipes WHERE name = 'Лёгкая Virginia Gold';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 7 FROM recipes WHERE name = 'Лёгкая Virginia Gold';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Лёгкая Virginia Gold';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 5 FROM recipes WHERE name = 'Лёгкая Virginia Gold';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Virginia', 24 FROM recipes WHERE name = 'Мягкая Virginia дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 36 FROM recipes WHERE name = 'Мягкая Virginia дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 26 FROM recipes WHERE name = 'Мягкая Virginia дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 6 FROM recipes WHERE name = 'Мягкая Virginia дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Мягкая Virginia дымная';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 5 FROM recipes WHERE name = 'Мягкая Virginia дымная';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Virginia', 22 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Burley', 10 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 31 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 24 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 5 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Баланс Virginia + Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 5 FROM recipes WHERE name = 'Баланс Virginia + Burley';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Burley', 24 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Virginia', 14 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 28 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 23 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 3 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Крепкая Burley + Virginia';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 5 FROM recipes WHERE name = 'Крепкая Burley + Virginia';

INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'tobacco', 'Burley', 40 FROM recipes WHERE name = 'Жаростойкая Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'glycerin', 'Глицерин', 27 FROM recipes WHERE name = 'Жаростойкая Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'gfs', 'ГФС', 23 FROM recipes WHERE name = 'Жаростойкая Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'propylene_glycol', 'Пропиленгликоль', 3 FROM recipes WHERE name = 'Жаростойкая Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'distilled_water', 'Дистиллированная вода', 3 FROM recipes WHERE name = 'Жаростойкая Burley';
INSERT INTO recipe_items (recipe_id, ingredient_kind, label, percent)
SELECT id, 'flavor', 'Ароматизатор', 4 FROM recipes WHERE name = 'Жаростойкая Burley';
