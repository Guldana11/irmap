from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from sqlalchemy.orm import Session
from models.user import User
from services.asset_stats import get_asset_stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_login(request: Request, db: Session = Depends(get_db)):
    email = request.session.get("user")
    if not email:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return RedirectResponse("/login", status_code=303)

    return user

@router.get("/dashboard")
def show_dashboard(request: Request, user: User = Depends(require_login)):
    total, critical = get_asset_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "Username": user.username,
        "AssetTotal": total,
        "AssetCritical": critical
    })
