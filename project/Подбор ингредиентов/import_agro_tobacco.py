from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import date

import requests

import database as db

BASE_URL = "https://agro-ukraine.com"
CATEGORY_URL = (
    BASE_URL
    + "/ru/trade/?adv_search=1&r_id=524&types_id=2&price_to=450&price_currency_id=2&page={page}"
)
VIEW_MODE_URL = BASE_URL + "/ru/trade/r-524/p-1/?cab=1&func=board_view_mode_set&set=1"
SPECIAL_URL = (
    BASE_URL
    + "/ru/trade/m-1354876/yakisnij-tyutyun-gavana-berli-virdzhiniya-runo-kemel-vinston-gold-priluki-bez-palichok/"
)
MAX_PRICE_UAH = 450
MIN_PRICE_UAH = 100
IMPORT_ONLY_SPECIAL_SELLER = True
TODAY = date.today().isoformat()


@dataclass
class Offer:
    title: str
    url: str
    price_uah: float
    seller: str
    region: str
    published: str
    description: str
    classification: str
    tobacco_type: str
    strength: str
    cut: str
    phone: str = ""
    telegram: str = ""
    viber: str = ""
    notes_extra: str = ""


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<.*?>", " ", value, flags=re.S)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    return value.strip()


def compact(value: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def parse_price(block: str) -> float | None:
    match = re.search(r'<span class="i_price">\s*([0-9 ]+)', block)
    if not match:
        return None
    return float(match.group(1).replace(" ", ""))


def kg_prices(text: str) -> list[float]:
    lower = text.lower().replace("\xa0", " ")
    prices: list[float] = []
    patterns = [
        r"(?<!\d)(\d{2,5})(?:\s*[-–]\s*(\d{2,5}))?\s*(?:грн|uah)\s*(?:/|за|\s)*(?:1\s*)?(?:кг|kg)",
        r"(?:кг|kg)\s*(?:по|за|:)?\s*(\d{2,5})(?:\s*[-–]\s*(\d{2,5}))?\s*(?:грн|uah)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, lower):
            prices.append(float(match.group(2) or match.group(1)))
    return prices


def has_tobacco_content(text: str) -> bool:
    lower = text.lower()
    tobacco_terms = [
        "тютюн",
        "табак",
        "тюн",
        "махор",
        "вірдж",
        "вирдж",
        "вердж",
        "virginia",
        "берл",
        "burley",
        "гаван",
        "дюб",
        "руно",
        "кемел",
        "camel",
        "вінстон",
        "винстон",
        "winston",
        "мальб",
        "marlboro",
        "парлам",
        "parliament",
        "кентук",
        "kentucky",
        "самосад",
    ]
    return any(term in lower for term in tobacco_terms)


def is_accessory_only(text: str) -> bool:
    lower = text.lower()
    accessory_terms = [
        "аксес",
        "гильз",
        "гільз",
        "машинк",
        "люльк",
        "мундштук",
        "портсигар",
        "бумага",
        "папір",
    ]
    return any(term in lower for term in accessory_terms) and not has_tobacco_content(lower)


def should_skip_offer_text(text: str) -> bool:
    lower = text.lower()
    if not has_tobacco_content(lower):
        return True
    if any(word in lower for word in ["розсад", "рассад", "семена", "насіння", "семя"]):
        return True
    if any(word in lower for word in ["консервант", "ароматизатор"]):
        return True
    if is_accessory_only(lower):
        return True
    found_kg_prices = kg_prices(lower)
    if found_kg_prices and min(found_kg_prices) > MAX_PRICE_UAH:
        return True
    return False


def classify(text: str) -> tuple[str, str, str, str]:
    lower = text.lower()
    varieties = [
        ("virginia", "Virginia"),
        ("вірдж", "Virginia"),
        ("вирдж", "Virginia"),
        ("вердж", "Virginia"),
        ("берлі", "Burley"),
        ("берли", "Burley"),
        ("берлей", "Burley"),
        ("burley", "Burley"),
        ("гавана", "Гавана"),
        ("havana", "Гавана"),
        ("руно", "Золотое Руно"),
        ("gold", "Gold"),
        ("голд", "Gold"),
        ("махор", "Махорка"),
        ("дюбек", "Дюбек"),
        ("дубек", "Дюбек"),
        ("кентук", "Kentucky"),
        ("ксанті", "Ксанти"),
        ("ксанти", "Ксанти"),
        ("самосад", "Самосад"),
        ("camel", "Camel"),
        ("кемел", "Camel"),
        ("winston", "Winston"),
        ("вінстон", "Winston"),
        ("винстон", "Winston"),
        ("marlboro", "Marlboro"),
        ("мальборо", "Marlboro"),
        ("parliament", "Parliament"),
        ("парламент", "Parliament"),
        ("прилуки", "Прилуки"),
    ]
    found: list[str] = []
    for needle, label in varieties:
        if needle in lower and label not in found:
            found.append(label)

    type_parts: list[str] = []
    if "імпорт" in lower or "импорт" in lower:
        type_parts.append("импортный")
    if "фабр" in lower:
        type_parts.append("фабричный")
    if "самосад" in lower or "власного вирощ" in lower:
        type_parts.append("домашнего выращивания")
    tobacco_type = ", ".join(type_parts) or "табак"

    strength = ""
    if "міцн" in lower or "крепк" in lower:
        strength = "крепкая"
    elif "середн" in lower or "средн" in lower:
        strength = "средняя"
    elif "легк" in lower or "легкий" in lower:
        strength = "легкая"

    cut = ""
    if "лапш" in lower:
        cut = "лапша"
    elif "паутин" in lower or "павутин" in lower:
        cut = "паутинка"
    elif "різан" in lower or "резан" in lower:
        cut = "резаный"
    elif "очищ" in lower or "без сміт" in lower or "без смит" in lower:
        cut = "очищенный"

    return ", ".join(found), tobacco_type, strength, cut


def parse_listing_block(block: str) -> Offer | None:
    title_match = re.search(r'<a\s+href="([^"]+)"\s+class="i_title ff2">(.*?)</a>', block, flags=re.S)
    if not title_match:
        return None
    price = parse_price(block)
    if price is None or price < MIN_PRICE_UAH or price > MAX_PRICE_UAH:
        return None

    url = html.unescape(title_match.group(1))
    title = strip_tags(title_match.group(2))

    text_match = re.search(r'<div\s+class="i_text">(.*?)</div>', block, flags=re.S)
    description = strip_tags(text_match.group(1)) if text_match else ""
    combined_lower = f"{title} {description}".lower()
    if should_skip_offer_text(combined_lower):
        return None

    contact_match = re.search(r'<div\s+class="i_cdt">(.*?)</div><!-- ad contacts -->', block, flags=re.S)
    seller = ""
    region = ""
    published = ""
    if contact_match:
        cdt = strip_tags(contact_match.group(1))
        parts = [part.strip() for part in cdt.split(",") if part.strip()]
        seller = parts[0] if parts else ""
        region = parts[1] if len(parts) > 1 else ""
        date_match = re.search(r"\b\d{2}-\d{2}-\d{4}\b", cdt)
        published = date_match.group(0) if date_match else ""

    classification, tobacco_type, strength, cut = classify(f"{title} {description}")
    return Offer(
        title=title,
        url=url,
        price_uah=price,
        seller=seller,
        region=region,
        published=published,
        description=description,
        classification=classification,
        tobacco_type=tobacco_type,
        strength=strength,
        cut=cut,
    )


def fetch_listing_offers(session: requests.Session) -> list[Offer]:
    offers: list[Offer] = []
    seen_urls: set[str] = set()
    for page in range(1, 100):
        response = None
        for attempt in range(3):
            response = session.get(CATEGORY_URL.format(page=page), timeout=25)
            if response.status_code != 503:
                break
            time.sleep(2 + attempt * 3)
        if response is None:
            break
        if response.status_code in {404, 503} and page > 1:
            break
        response.raise_for_status()
        blocks = re.findall(
            r'<div\s+class="i_l_i_c_mode1.*?</div><!-- ads container ==<< -->',
            response.text,
            flags=re.S,
        )
        if not blocks:
            break
        for block in blocks:
            offer = parse_listing_block(block)
            if offer and offer.url not in seen_urls:
                offers.append(offer)
                seen_urls.add(offer.url)
        time.sleep(0.2)
    return offers


def enrich_special_offer(session: requests.Session, offers: list[Offer]) -> None:
    response = None
    for attempt in range(3):
        response = session.get(SPECIAL_URL, timeout=25)
        if response.status_code != 503:
            break
        time.sleep(2 + attempt * 3)

    fallback_title = "Якісний тютюн Гавана, Берлі, Вірджинія, Руно, Кемел, Вінстон, Голд, Прилуки без паличок"
    fallback_plain = (
        fallback_title
        + " Гавана Прилуки Міленіум Золоте Руно Давідофф Капітан Блек "
        + "Вірджинія Голд Берлі Дюбек Махорка Венгерський локшина павутинка фабричний пластівці"
    )
    if response is not None and response.ok:
        text = response.text
        plain = strip_tags(text)
        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.S)
        title = strip_tags(title_match.group(1)) if title_match else fallback_title
        price_match = re.search(r'<span class="item_price">\s*([0-9 ]+)', text)
        if not price_match:
            price_match = re.search(r"([0-9]{2,5})\s*грн", plain)
        price = float(price_match.group(1).replace(" ", "")) if price_match else 450.0

        phone_match = re.search(r"\(?0\d{2}\)?[\s-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}", plain)
        phone = phone_match.group(0).strip() if phone_match else ""
        viber_match = re.search(r"Viber\s*[:\-]?\s*(\+?\d[\d\s()-]{8,})", plain, flags=re.I)
        viber = viber_match.group(1).strip() if viber_match else phone
        telegram = ""
        for telegram_match in re.finditer(r"Telegram\s*[:\-]?\s*([^\n\r ]+)", plain, flags=re.I):
            candidate = telegram_match.group(1).strip()
            if candidate.startswith(("+", "@")) or "t.me" in candidate:
                telegram = candidate
                break
    else:
        plain = fallback_plain
        title = fallback_title
        price = 450.0
        phone = "(093) 207-26-59"
        viber = "380932072659"
        telegram = "+o-crMGoJ4KdlNDBi"

    classification, tobacco_type, strength, cut = classify(plain)
    description = "Гавана, Берлі, Вірджинія, Руно, Кемел, Вінстон Gold, Прилуки; без паличок; от 500 г."
    notes_extra = (
        "Приоритетный продавец из ссылки пользователя. По карточке: продавец Михайло, "
        "Кировоградская обл.; отправка Новой Почтой/Укрпоштой; связь через звонок, Viber и Telegram."
    )

    existing = next((offer for offer in offers if offer.url.rstrip("/") == SPECIAL_URL.rstrip("/")), None)
    if existing:
        existing.title = title
        existing.price_uah = price
        existing.seller = existing.seller or "Михайло"
        existing.region = existing.region or "Кировоградская обл."
        existing.description = description
        existing.classification = classification or existing.classification
        existing.tobacco_type = tobacco_type or existing.tobacco_type
        existing.strength = strength or existing.strength
        existing.cut = cut or existing.cut
        existing.phone = phone
        existing.viber = viber
        existing.telegram = telegram
        existing.notes_extra = notes_extra
    else:
        offers.append(
            Offer(
                title=title,
                url=SPECIAL_URL,
                price_uah=price,
                seller="Михайло",
                region="Кировоградская обл.",
                published="",
                description=description,
                classification=classification,
                tobacco_type=tobacco_type,
                strength=strength,
                cut=cut,
                phone=phone,
                viber=viber,
                telegram=telegram,
                notes_extra=notes_extra,
            )
        )


def save_offers(offers: list[Offer]) -> None:
    db.init_db()
    with db.session(db.DB_PATH) as conn:
        if IMPORT_ONLY_SPECIAL_SELLER:
            conn.execute("DELETE FROM tobacco")
        else:
            conn.execute("DELETE FROM tobacco WHERE coalesce(url, '') LIKE 'https://agro-ukraine.com/%'")

    for offer in offers:
        classifications = db.split_reference_text(offer.classification) or [""]
        for classification in classifications:
            short_name = db.build_tobacco_name(classification, offer.seller or "Agro-Ukraine", offer.strength)
            notes = [
                f"Источник: Agro-Ukraine; импортировано {TODAY}.",
                f"Регион: {offer.region or 'не указан'}; дата объявления: {offer.published or 'не указана'}.",
                "Цена внесена как упаковка 1000 г для сравнения; перед покупкой подтвердить фасовку и актуальность.",
                f"Исходное название объявления: {offer.title}",
            ]
            if offer.notes_extra:
                notes.append(offer.notes_extra)
            if offer.description:
                notes.append("Описание: " + compact(offer.description, 220))
            db.save_item(
                "tobacco",
                {
                    "name": short_name,
                    "price_uah": offer.price_uah,
                    "package_amount_g": 1000,
                    "manufacturer": "",
                    "seller": offer.seller or "Agro-Ukraine",
                    "url": offer.url,
                    "phone": offer.phone,
                    "telegram": offer.telegram,
                    "viber": offer.viber,
                    "email": "",
                    "classification": classification,
                    "tobacco_type": offer.tobacco_type,
                    "strength": offer.strength,
                    "cut": offer.cut,
                    "notes": "\n".join(notes),
                },
            )


def main() -> None:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            )
        }
    )
    session.get(VIEW_MODE_URL, timeout=25)
    offers = [] if IMPORT_ONLY_SPECIAL_SELLER else fetch_listing_offers(session)
    enrich_special_offer(session, offers)
    offers.sort(key=lambda item: (item.price_uah, item.seller.lower(), item.title.lower()))
    save_offers(offers)
    print(f"Imported Agro-Ukraine tobacco offers: {len(offers)}")
    print(f"Price filter: {MIN_PRICE_UAH}-{MAX_PRICE_UAH} UAH")
    print(f"Special seller URL included: {SPECIAL_URL}")


if __name__ == "__main__":
    main()
