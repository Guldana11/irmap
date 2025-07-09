from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import SessionLocal
from models.user import User
from passlib.hash import bcrypt
from config.sms import send_telegram_code
import pyotp, random, string
from datetime import datetime, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="templates")

verification_codes = {}
totp_secrets = {}
verification_expiry = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/login")
def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request,  "user": User})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
    ):
    user = db.query(User).filter(User.email == email).first()

    if not user or not bcrypt.verify(password, user.password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"}
        )

    # ❗ Сохраняем только email в сессию
    request.session["user"] = email

    return RedirectResponse("/dashboard", status_code=303)

@router.get("/register")
def show_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    method: str = Form(...),
    telegram_chat_id: str = Form(None),
    db: Session = Depends(get_db)
    ):
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email уже зарегистрирован"})

    code = generate_code()
    hashed = bcrypt.hash(password)

    request.session["pending_email"] = email
    request.session["pending_password"] = password
    request.session["pending_method"] = method
    request.session["pending_chat_id"] = telegram_chat_id
    
    print("📨 Код сохранён в сессию:", code)

    if method == "telegram":
        if not telegram_chat_id:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Введите Telegram chat ID"})

        verification_codes[email] = code
        verification_expiry[email] = datetime.utcnow() + timedelta(minutes=5)
        send_telegram_code(telegram_chat_id, code)
        return RedirectResponse(f"/verify/{email}", status_code=303)


    elif method == "totp":
        secret = pyotp.random_base32()
        totp_secrets[email] = secret
        verification_expiry[email] = datetime.utcnow() + timedelta(minutes=5)

        request.session["totp_secret"] = secret

        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="IRMAP")
        return templates.TemplateResponse("verify_totp.html", {
            "request": request,
            "qr": totp_uri,
            "email": email
        })

    return templates.TemplateResponse("register.html", {"request": request, "error": "Выберите метод 2FA"})

@router.get("/verify/{email}")
def show_verify(request: Request, email: str):
    return templates.TemplateResponse("verify.html", {"request": request, "email": email})

@router.post("/verify/{email}")
def verify_code(
    request: Request,
    email: str,
    code: str = Form(...),
    db: Session = Depends(get_db)
    ):
    print("✅ Получен код из формы:", code)
    print("🧠 Ожидаемый код из памяти:", verification_codes.get(email))

    method = request.session.get("pending_method")
    if not method:
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "email": email,
            "error": "Метод не найден"
        })

    expires_at = verification_expiry.get(email)
    if not expires_at or datetime.utcnow() > expires_at:
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "email": email,
            "error": "Срок действия кода истёк. Пожалуйста, отправьте код повторно."
        })

    if method == "totp":
        secret = request.session.get("totp_secret")
        if not secret or not pyotp.TOTP(secret).verify(code):
            return templates.TemplateResponse("verify.html", {
                "request": request,
                "email": email,
                "error": "Неверный TOTP-код"
            })

    elif method == "telegram":
        expected = verification_codes.get(email)
        actual = str(code).strip()
        print(" Сравнение:", repr(expected), "vs", repr(actual))

        if not expected or expected != actual:
            return templates.TemplateResponse("verify.html", {
                "request": request,
                "email": email,
                "error": "Неверный код подтверждения"
            })

    else:
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "email": email,
            "error": "Неизвестный метод 2FA"
        })

    hashed_password = bcrypt.hash(request.session.get("pending_password"))
    user = User(
        email=email,
        password=hashed_password,
        two_fa_method=method,
        telegram_chat_id=request.session.get("pending_chat_id"),
        totp_secret=request.session.get("totp_secret") if method == "totp" else None
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    for key in ["pending_email", "pending_password", "pending_method", "pending_chat_id", "totp_secret"]:
        request.session.pop(key, None)
    verification_codes.pop(email, None)
    verification_expiry.pop(email, None)

    request.session["user"] = {"username": email}

    return RedirectResponse("/dashboard", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

def generate_code():
    return ''.join(random.choices(string.digits, k=6))
