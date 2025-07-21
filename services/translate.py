def translate_priority(priority: str, lang: str) -> str:
    translations = {
        "критический": "Критикалық",
        "высокий": "Жоғары",
        "средний": "Орташа",
        "низкий": "Төмен",
    }
    if lang == "kz":
        return translations.get(priority.lower(), priority)
    return priority

def translate_status(status: str, lang: str) -> str:
    translations = {
        "новый": "Жаңа",
        "в работе": "Жұмыс барысында",
        "снижен": "Азайтылған",
        "закрыт": "Жабық",
    }
    if lang == "kz":
        return translations.get(status.lower(), status)
    return status
