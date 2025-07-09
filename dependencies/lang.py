from fastapi import Request

def get_lang(request: Request) -> str:
    lang = request.cookies.get("lang")
    return lang if lang in ["ru", "kz"] else "ru"