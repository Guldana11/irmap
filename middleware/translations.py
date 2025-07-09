import gettext
from fastapi.templating import Jinja2Templates
from fastapi import Request

def install_translations(request: Request, templates: Jinja2Templates):
    lang = request.query_params.get("lang", "ru")
    t = gettext.translation(
        domain="messages",
        localedir="translations",
        languages=[lang],
        fallback=True
    )
    # Устанавливает глобальный _() для Python (не обязательно)
    t.install()
    # Обязательно: делает _() доступным в шаблонах
    templates.env.globals["_"] = t.gettext
