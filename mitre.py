import json
from deep_translator import GoogleTranslator

INPUT_FILE = "enterprise-attack.json"
OUTPUT_FILE = "enterprise-attack_translated.json"
LIMIT = 100

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f).get("objects", [])

translated_items = []

for i, item in enumerate(data):
    if i >= LIMIT:
        break

    name_en = item.get("name", "")
    description_en = item.get("description", "")

    print(f"Переводим: {name_en}...")

    try:
        name_ru = GoogleTranslator(source='en', target='ru').translate(name_en)
    except Exception as e:
        print(f"Ошибка перевода имени на русский: {e}")
        name_ru = name_en

    try:
        name_kz = GoogleTranslator(source='en', target='kk').translate(name_en)
    except Exception as e:
        print(f"Ошибка перевода имени на казахский: {e}")
        name_kz = name_en

    try:
        description_ru = GoogleTranslator(source='en', target='ru').translate(description_en) if description_en else ""
    except Exception as e:
        print(f"Ошибка перевода описания на русский: {e}")
        description_ru = description_en

    try:
        description_kz = GoogleTranslator(source='en', target='kk').translate(description_en) if description_en else ""
    except Exception as e:
        print(f"Ошибка перевода описания на казахский: {e}")
        description_kz = description_en

    item["name_ru"] = name_ru
    item["name_kz"] = name_kz
    item["description"] = description_ru
    item["description_ru"] = description_ru
    item["description_kz"] = description_kz

    translated_items.append(item)

# Сохраняем только 50 переведённых
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(translated_items, f, ensure_ascii=False, indent=2)

print(f"✅ Переведено и сохранено 100 угроз в {OUTPUT_FILE}")
