from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.user import User
from db import SessionLocal  

profile_router = APIRouter()
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@profile_router.get("/profile/data")
def get_profile_data(request: Request, db: Session = Depends(get_db)):
    email = request.session.get("user")
    if not email:
        return JSONResponse(status_code=401, content={"error": "Не авторизован"})

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "Пользователь не найден"})

    return JSONResponse(status_code=200, content={
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "position": user.position,
        "created_at": str(user.created_at) if user.created_at else None
    })

@profile_router.post("/profile/update")
def update_profile(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    db: Session = Depends(get_db)
    ):
    email = request.session.get("user")
    if not email:
        return JSONResponse(status_code=401, content={"error": "Неавторизован"})

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "Пользователь не найден"})

    user.full_name = full_name
    user.phone = phone
    user.position = position
    db.commit()
    db.refresh(user)
    return JSONResponse(status_code=200, content={"message": "Профиль обновлён"})