from __future__ import annotations

from datetime import date

import database as db

SELLER_NAME = "Алиса / Табачок"
SELLER_URL = "https://agro-ukraine.com/ru/trade/m-1125130/bond-kemel-rotmans-vest-ld-priluki-vinston-parlament-malboro/"
PHONE = "0996302334; 0663864881; 0963170049"
TELEGRAM = "@tyt_vsetvoe"
VIBER = "075-664-84-12"
IMPORT_TAG = "Источник: прайс Telegram @tyt_vsetvoe"
TODAY = date.today().isoformat()


TOBACCO_ITEMS = [
    {
        "classification": "Burley",
        "display": "Burley",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "",
        "type": "табак",
        "source": "Берлей (середній/міцний)",
    },
    {
        "classification": "Marlboro",
        "display": "Marlboro",
        "strengths": ["средняя"],
        "price": 1200,
        "cut": "лапша",
        "type": "для гильз",
        "source": "Мальберо середній (лапша) для гільз",
    },
    {
        "classification": "Virginia",
        "display": "Virginia",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "лапша/ломаная",
        "type": "для гильз",
        "source": "Вірджинія для гільз (лапша/ломана) середня міцність/міцна",
    },
    {
        "classification": "Virginia Gold",
        "display": "Virginia Gold",
        "strengths": ["легкая", "средняя"],
        "price": 1650,
        "cut": "лапша",
        "type": "для гильз",
        "source": "Вірджинія Голд (лапша для гільз) легка/середня міцність",
    },
    {
        "classification": "Winston",
        "display": "Winston",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "лапша",
        "type": "табак",
        "source": "Вінстон (лапша) середня/міцна",
    },
    {
        "classification": "Міленіум",
        "display": "Міленіум",
        "strengths": ["средняя"],
        "price": 1200,
        "cut": "ломаная лапша",
        "type": "для гильз",
        "source": "Міленіум (ломана лапша) для гільз, середня міцність",
    },
    {
        "classification": "Золотое Руно",
        "display": "Золотое Руно",
        "strengths": [""],
        "price": 1650,
        "cut": "ломаная лапша",
        "type": "классический вкус",
        "source": "Золоте Руно класичний смак (ломана лапша)",
    },
    {
        "classification": "Дюбек",
        "display": "Дюбек",
        "strengths": ["крепкая"],
        "price": 1200,
        "cut": "лапша",
        "type": "для гильз",
        "source": "Дюбек міцний (лапша) для гільз",
    },
    {
        "classification": "Капитан Блек",
        "display": "Капитан Блек вишня",
        "strengths": ["средняя"],
        "price": 1350,
        "cut": "лапша",
        "type": "ароматизированный: вишня; для гильз",
        "source": "КАП БЛЕК ВИШНЯ середній (лапша) для гільз",
    },
    {
        "classification": "Капитан Блек",
        "display": "Капитан Блек шоколад",
        "strengths": ["средняя"],
        "price": 1350,
        "cut": "лапша",
        "type": "ароматизированный: шоколад; для гильз",
        "source": "КАП БЛЕК ШОКОЛАД середній (лапша) для гільз",
    },
    {
        "classification": "Virginia",
        "display": "Virginia хлопья",
        "strengths": [""],
        "price": 1150,
        "cut": "хлопья",
        "type": "табак",
        "source": "Вірджинія ХЛОП'Я",
    },
    {
        "classification": "Махорка",
        "display": "Махорка",
        "strengths": ["средняя", "крепкая"],
        "price": 1150,
        "cut": "",
        "type": "табак",
        "source": "Махорка середня/міцна",
    },
    {
        "classification": "Кентуки",
        "display": "Кентуки",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "лапша",
        "type": "табак",
        "source": "Кентукі средній/міцний лапша",
    },
    {
        "classification": "Прилуки",
        "display": "Прилуки",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "лапша",
        "type": "табак",
        "source": "Прилуки средній/міцний лапша",
    },
    {
        "classification": "Camel",
        "display": "Camel",
        "strengths": ["средняя"],
        "price": 1200,
        "cut": "",
        "type": "табак",
        "source": "Кемел середній",
    },
    {
        "classification": "Parliament",
        "display": "Parliament",
        "strengths": ["средняя"],
        "price": 1200,
        "cut": "",
        "type": "табак",
        "source": "Парламент середній",
    },
    {
        "classification": "Гавана",
        "display": "Гавана",
        "strengths": ["средняя", "крепкая"],
        "price": 1200,
        "cut": "ломаная лапша",
        "type": "для гильз",
        "source": "Гавана середня/міцна (ломана лапша) для гільз",
    },
    {
        "classification": "Давидофф",
        "display": "Давидофф",
        "strengths": ["средняя"],
        "price": 1650,
        "cut": "",
        "type": "табак",
        "source": "Давідофф середній",
    },
]


def build_name(display: str, strength: str) -> str:
    name = f"{display} - {SELLER_NAME}"
    if strength:
        name += f" ({strength})"
    return name


def notes_for(item: dict, strength: str) -> str:
    lines = [
        f"{IMPORT_TAG}; импортировано {TODAY}.",
        "В прайсе указано: цена за 1 кг, есть фасовка по 500 г.",
        "Сайт Agro-Ukraine показывает другую витринную цену; для базы использован прайс из Telegram/Viber.",
        "Отправка по прайсу: в течение 3 дней с момента заказа.",
        "График: ПН-ПТ 10:00-18:00, суббота до 14:00, воскресенье выходной.",
        f"Позиция прайса: {item['source']}.",
    ]
    if strength:
        lines.append(f"Крепость из прайса: {strength}.")
    return "\n".join(lines)


def main() -> None:
    db.init_db()
    with db.session(db.DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM tobacco
            WHERE url = ?
               OR telegram = ?
               OR notes LIKE ?
            """,
            (SELLER_URL, TELEGRAM, f"%{IMPORT_TAG}%"),
        )

    inserted = 0
    for item in TOBACCO_ITEMS:
        for strength in item["strengths"]:
            db.save_item(
                "tobacco",
                {
                    "name": build_name(item["display"], strength),
                    "price_uah": item["price"],
                    "package_amount_g": 1000,
                    "manufacturer": "",
                    "seller": SELLER_NAME,
                    "url": SELLER_URL,
                    "phone": PHONE,
                    "telegram": TELEGRAM,
                    "viber": VIBER,
                    "email": "",
                    "classification": item["classification"],
                    "tobacco_type": item["type"],
                    "strength": strength,
                    "cut": item["cut"],
                    "notes": notes_for(item, strength),
                },
            )
            inserted += 1

    print(f"Imported {inserted} tobacco rows for {SELLER_NAME}")
    print(f"Source: {SELLER_URL}")


if __name__ == "__main__":
    main()
