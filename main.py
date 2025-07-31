from fastapi import FastAPI, Request, Query, Depends
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

from routes import auth, asset, cmdb_import
from routes.profile import profile_router
from db import init_db, SessionLocal, get_db
from apscheduler.schedulers.background import BackgroundScheduler
from routes.cmdb_import import import_from_glpi
from dotenv import load_dotenv
from models.asset import Asset
from models.risk_assessment import RiskAssessment
from models.risk_map import RiskListEntry
from models.measure import Measure, Notification
from routes import risk_assessment, risk_map, measure

load_dotenv()

templates = Jinja2Templates(directory="templates")

class InjectUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public_paths = ["/login", "/register", "/static", "/"]

        user = None
        if "session" in request.scope:
            user_val = request.session.get("user")
            
            if isinstance(user_val, str):
                user = {"username": user_val}
            elif isinstance(user_val, dict):
                user = user_val

        request.state.user = user

        if not user and not any(path.startswith(p) for p in public_paths):
            return RedirectResponse("/login", status_code=303)

        return await call_next(request)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="your-super-secret-key")
app.add_middleware(InjectUserMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

init_db()

app.include_router(risk_map.router)
app.include_router(auth.router)
app.include_router(profile_router)
app.include_router(asset.router)
app.include_router(cmdb_import.router, prefix="/cmdb")
app.include_router(risk_assessment.router)
app.include_router(measure.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if isinstance(user, str):
        user = {"username": user}

    total_assets = db.query(Asset).count()
    total_risks = db.query(RiskAssessment).count()
    high_risks = db.query(RiskAssessment).filter(RiskAssessment.level.in_(['Высокий', 'Критический'])).count()
    high_critical_count = db.query(Asset).filter(Asset.criticality == "High").count()
    critical_priority_count=db.query(RiskListEntry).filter(RiskListEntry.priority.in_(['Критический'])).count()
    new_status_count=db.query(RiskListEntry).filter(RiskListEntry.status.in_(['Новый'])).count()
    in_progress_count = db.query(RiskListEntry).filter(RiskListEntry.status.in_(['В работе'])).count()
    total_measures = db.query(Measure).count()
    total_notifications = db.query(Notification).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user":user, 
            "total_assets": total_assets,
            "total_risks": total_risks,
            "high_risks": high_risks,
            "high_critical_count": high_critical_count,
            "critical_priority_count": critical_priority_count,
            "new_status_count": new_status_count,
            "in_progress_count": in_progress_count,
            "total_measures": total_measures,  
            "total_notifications": total_notifications  
        }
    )

def auto_import_job():
    db = SessionLocal()
    try:
        import_from_glpi(db)
    finally:
        db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_import_job, 'interval', minutes=30)
    scheduler.start()

