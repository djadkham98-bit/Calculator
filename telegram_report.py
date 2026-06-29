"""
telegram_report.py — отправляет выручку за вчера + топ-5 товаров в Telegram.
Запускать каждое утро в 9:00 через планировщик Windows.
"""

import sys
import requests
from datetime import datetime, timedelta, timezone

# Конфигурация (токен и chat_id — в tg_config.py)
try:
    from tg_config import TG_TOKEN, TG_CHAT_ID, API_URL
except ImportError:
    print("Ошибка: файл tg_config.py не найден рядом со скриптом.")
    sys.exit(1)

TZ = timezone(timedelta(hours=5))

MONTH_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

GROUPS = [
    ("🏙 ТАШКЕНТ",   ["Кадышева", "Чорсу"]),
    ("🏔 САМАРКАНД", ["Азиз бозор", "Мархабо"]),
    ("🏪 BONASERA",  ["Согдиана", "Узбекистанский", "Bonasera Men"]),
]


def fmt(n):
    """Форматирует число с пробелами как разделителями тысяч."""
    return f"{round(n):,}".replace(",", " ")


def get_report(date_str=None):
    url = f"{API_URL}/revenue-report"
    if date_str:
        url += f"?date={date_str}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"API вернул ошибку: {data}")
    return data


def build_message(data):
    date_str = data["date"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{dt.day} {MONTH_RU[dt.month]} {dt.year}"

    lines = [f"📊 *Выручка за {date_label}*", ""]

    revenue = data["revenue"]
    for group_label, stores in GROUPS:
        group_total = sum(revenue.get(s, 0) for s in stores)
        if group_total == 0:
            continue
        lines.append(group_label)
        for store in stores:
            val = revenue.get(store, 0)
            if val > 0:
                lines.append(f"  • {store}: {fmt(val)} сум")
        lines.append("")

    lines.append("━━━━━━━━━━━━━")
    lines.append(f"*ИТОГО: {fmt(data['grand_total'])} сум*")

    top5 = data.get("top5_qty", [])
    if top5:
        lines.append("")
        lines.append("🔥 *Топ-5 товаров дня*")
        medals = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, item in enumerate(top5):
            lines.append(f"{medals[i]} {item['name']} — {fmt(item['qty'])} шт")

    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    # Можно передать дату аргументом: python telegram_report.py 2026-06-28
    date_str = sys.argv[1] if len(sys.argv) > 1 else None

    print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] Запрашиваю данные...")
    data = get_report(date_str)

    message = build_message(data)
    print("Сообщение:")
    print(message)
    print()

    print("Отправляю в Telegram...")
    result = send_telegram(message)
    if result.get("ok"):
        print("✓ Успешно отправлено!")
    else:
        print(f"✗ Ошибка Telegram: {result}")


if __name__ == "__main__":
    main()
