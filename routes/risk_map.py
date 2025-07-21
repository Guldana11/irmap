from fastapi import FastAPI, Request, APIRouter, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
import pandas as pd
from reportlab.pdfbase.ttfonts import TTFont
import io
from reportlab.pdfgen import canvas
from db import get_db
from models.risk_map import RiskListEntry
from models.schemas import RiskListEntryOut, RiskCreateSchema, RiskUpdateSchema  
from typing import List
from dependencies.lang import get_lang


app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="templates")
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf')) 
router = APIRouter()

@router.get("/risk_map", response_class=HTMLResponse)
async def risk_map(request: Request,
    db: Session = Depends(get_db),
    lang: str = Depends(get_lang)
    ):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if isinstance(user, str):
        user = {"username": user}
            
    risks = db.query(RiskListEntry).all()
    return templates.TemplateResponse("risk_map.html", {
        "request": request,
        "user": user,
        "risks": risks,
        "lang": lang
    })

app.include_router(router)

@router.get("/api/risk-list")
async def get_risk_list(
    lang: str = Query("ru", enum=["ru", "kz"]),
    status: str = Query(None),
    department: str = Query(None),
    db: Session = Depends(get_db)
    ):
    query = db.query(RiskListEntry)

    if status:
        query = query.filter(RiskListEntry.status == status)

    if department:
        query = query.filter(RiskListEntry.department == department)

    risks = query.order_by(RiskListEntry.created_at.desc()).all()

    def localize(risk):
        return {
            "id": risk.id,
            "title": risk.title_kz if lang == "kz" else risk.title,
            "likelihood": risk.likelihood,
            "impact": risk.impact,
            "priority": risk.priority,
            "priority_class": risk.priority.lower(),
            "status": risk.status,
            "department": risk.department or "",
            "created_at": risk.created_at,
        }

    return [localize(r) for r in risks]


@router.post("/api/risk-list")
def create_risk(risk: RiskCreateSchema, db: Session = Depends(get_db)):
    new_risk = RiskListEntry(
        title=risk.title,
        title_kz=risk.title_kz,
        department=risk.department,
        likelihood=risk.likelihood,
        impact=risk.impact,
        priority=risk.priority,
        status=risk.status,
    )
    db.add(new_risk)
    db.commit()
    db.refresh(new_risk)
    return {"id": new_risk.id}
   

@router.delete("/api/risk-list/{risk_id}")
def delete_risk(risk_id: int, db: Session = Depends(get_db)):
    risk = db.query(RiskListEntry).filter(RiskListEntry.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    db.delete(risk)
    db.commit()
    return {"ok": True}

@router.get("/api/risk-list/{risk_id}")
def get_risk_by_id(
    risk_id: int,
    lang: str = Query("ru", enum=["ru", "kz"]),
    db: Session = Depends(get_db)
    ):
    risk = db.query(RiskListEntry).filter(RiskListEntry.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    return {
        "id": risk.id,
        "title": risk.title_kz if lang == "kz" else risk.title,
        "department": risk.department,
        "likelihood": risk.likelihood,
        "impact": risk.impact,
        "priority": translate_priority(risk.priority, lang),
        "status": translate_status(risk.status, lang),
        "created_at": risk.created_at,
    }

@router.put("/api/risk-list/{risk_id}")
def update_risk(risk_id: int, updated: RiskUpdateSchema, db: Session = Depends(get_db)):
    risk = db.query(RiskListEntry).filter(RiskListEntry.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    risk.likelihood = updated.likelihood
    risk.impact = updated.impact
    risk.priority = updated.priority
    risk.status = updated.status

    db.commit()
    db.refresh(risk)

    return {"id": risk.id}

@router.get("/risk_map/export/excel")
async def export_risk_map_excel(
    lang: str = "ru",
    type: str = "",
    department: str = "",
    status: str = "",
    priority: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(get_db)
    ):
    risks = db.query(RiskListEntry).order_by(RiskListEntry.created_at.desc()).all()

    headers = {
        "ru": {
            "department": "Подразделение",
            "title": "Название",
            "likelihood": "Вероятность",
            "impact": "Влияние",
            "priority": "Приоритет",
            "status": "Статус",
            "date": "Дата",
        },
        "kz": {
            "department": "Бөлімше",
            "title": "Атауы",
            "likelihood": "Ықтималдық",
            "impact": "Әсері",
            "priority": "Басымдық",
            "status": "Статус",
            "date": "Күні",
        }
    }

    department_map = {
        'it отдел': {'ru': 'IT отдел', 'kz': 'IT бөлімі'},
        'it бөлімі': {'ru': 'IT отдел', 'kz': 'IT бөлімі'},
        'бухгалтерия': {'ru': 'Бухгалтерия', 'kz': 'Бухгалтерия'},
        'отдел продаж': {'ru': 'Отдел продаж', 'kz': 'Сату бөлімі'},
        'сату бөлімі': {'ru': 'Отдел продаж', 'kz': 'Сату бөлімі'},
        'финансовый отдел': {'ru': 'Финансовый отдел', 'kz': 'Қаржы бөлімі'},
        'қаржы бөлімі': {'ru': 'Финансовый отдел', 'kz': 'Қаржы бөлімі'},
        'администрация': {'ru': 'Администрация', 'kz': 'Әкімшілік'},
        'әкімшілік': {'ru': 'Администрация', 'kz': 'Әкімшілік'},
        'служба поддержка': {'ru': 'Служба поддержка', 'kz': 'Қолдау қызметі'},
        'қолдау қызметі': {'ru': 'Служба поддержка', 'kz': 'Қолдау қызметі'},
    }

    status_map = {
        'новый': {'ru': 'Новый', 'kz': 'Жаңа'},
        'жаңа': {'ru': 'Новый', 'kz': 'Жаңа'},
        'в работе': {'ru': 'В работе', 'kz': 'Жұмыс барысында'},
        'жұмыс барысында': {'ru': 'В работе', 'kz': 'Жұмыс барысында'},
        'снижен': {'ru': 'Снижен', 'kz': 'Азайтылған'},
        'азайтылған': {'ru': 'Снижен', 'kz': 'Азайтылған'},
        'закрыт': {'ru': 'Закрыт', 'kz': 'Жабық'},
        'жабық': {'ru': 'Закрыт', 'kz': 'Жабық'},
    }

    priority_map = {
        'низкий': {'ru': 'Низкий', 'kz': 'Төмен'},
        'төмен': {'ru': 'Низкий', 'kz': 'Төмен'},
        'средний': {'ru': 'Средний', 'kz': 'Орташа'},
        'орташа': {'ru': 'Средний', 'kz': 'Орташа'},
        'высокий': {'ru': 'Высокий', 'kz': 'Жоғары'},
        'жоғары': {'ru': 'Высокий', 'kz': 'Жоғары'},
        'критический': {'ru': 'Критический', 'kz': 'Шұғыл'},
        'шұғыл': {'ru': 'Критический', 'kz': 'Шұғыл'},
    }

    def match(risk):
        title_check = (risk.title_kz or risk.title or '').lower()
        if type and type not in title_check:
            return False

        dept_key = (risk.department or '').strip().lower()
        if department:
            for key, val in department_map.items():
                if key == dept_key:
                    if department.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        status_key = (risk.status or '').strip().lower()
        if status:
            for key, val in status_map.items():
                if key == status_key:
                    if status.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        priority_key = (risk.priority or '').strip().lower()
        if priority:
            for key, val in priority_map.items():
                if key == priority_key:
                    if priority.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        if dateFrom and risk.created_at.strftime('%Y-%m-%d') < dateFrom:
            return False
        if dateTo and risk.created_at.strftime('%Y-%m-%d') > dateTo:
            return False

        return True

    filtered_risks = list(filter(match, risks))
    export_data = filtered_risks if any([type, department, status, priority, dateFrom, dateTo]) else risks

    data = []
    for risk in export_data:
        priority_key = (risk.priority or '').strip().lower()
        status_key = (risk.status or '').strip().lower()
        dept_key = (risk.department or '').strip().lower()

        row = {
            "ID": f"RISK-{risk.id:03d}",
            headers[lang]["department"]: department_map.get(dept_key, {}).get(lang, risk.department),
            headers[lang]["title"]: risk.title if lang == "ru" else risk.title_kz,
            headers[lang]["likelihood"]: risk.likelihood,
            headers[lang]["impact"]: risk.impact,
            headers[lang]["priority"]: priority_map.get(priority_key, {}).get(lang, risk.priority),
            headers[lang]["status"]: status_map.get(status_key, {}).get(lang, risk.status),
            headers[lang]["date"]: risk.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        data.append(row)

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Risk Map', index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=risk_map_export.xlsx"}
    )

@router.get("/risk_map/export/pdf")
async def export_risk_map_pdf(
    lang: str = "ru",
    type: str = "",
    department: str = "",
    status: str = "",
    priority: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(get_db)
    ):
    risks = db.query(RiskListEntry).order_by(RiskListEntry.created_at.desc()).all()

    headings = {
        "ru": ["ID", "Подразделение", "Название", "Вероятность", "Влияние", "Приоритет", "Статус", "Дата"],
        "kz": ["ID", "Бөлімше", "Атауы", "Ықтималдық", "Әсері", "Басымдық", "Статус", "Күні"]
    }

    department_map = {
        'it отдел': {'ru': 'IT отдел', 'kz': 'IT бөлімі'},
        'it бөлімі': {'ru': 'IT отдел', 'kz': 'IT бөлімі'},
        'бухгалтерия': {'ru': 'Бухгалтерия', 'kz': 'Бухгалтерия'},
        'отдел продаж': {'ru': 'Отдел продаж', 'kz': 'Сату бөлімі'},
        'сату бөлімі': {'ru': 'Отдел продаж', 'kz': 'Сату бөлімі'},
        'финансовый отдел': {'ru': 'Финансовый отдел', 'kz': 'Қаржы бөлімі'},
        'қаржы бөлімі': {'ru': 'Финансовый отдел', 'kz': 'Қаржы бөлімі'},
        'администрация': {'ru': 'Администрация', 'kz': 'Әкімшілік'},
        'әкімшілік': {'ru': 'Администрация', 'kz': 'Әкімшілік'},
        'служба поддержка': {'ru': 'Служба поддержка', 'kz': 'Қолдау қызметі'},
        'қолдау қызметі': {'ru': 'Служба поддержка', 'kz': 'Қолдау қызметі'},
    }

    status_map = {
        'новый': {'ru': 'Новый', 'kz': 'Жаңа'},
        'жаңа': {'ru': 'Новый', 'kz': 'Жаңа'},
        'в работе': {'ru': 'В работе', 'kz': 'Жұмыс барысында'},
        'жұмыс барысында': {'ru': 'В работе', 'kz': 'Жұмыс барысында'},
        'снижен': {'ru': 'Снижен', 'kz': 'Азайтылған'},
        'азайтылған': {'ru': 'Снижен', 'kz': 'Азайтылған'},
        'закрыт': {'ru': 'Закрыт', 'kz': 'Жабық'},
        'жабық': {'ru': 'Закрыт', 'kz': 'Жабық'},
    }

    priority_map = {
        'низкий': {'ru': 'Низкий', 'kz': 'Төмен'},
        'төмен': {'ru': 'Низкий', 'kz': 'Төмен'},
        'средний': {'ru': 'Средний', 'kz': 'Орташа'},
        'орташа': {'ru': 'Средний', 'kz': 'Орташа'},
        'высокий': {'ru': 'Высокий', 'kz': 'Жоғары'},
        'жоғары': {'ru': 'Высокий', 'kz': 'Жоғары'},
        'критический': {'ru': 'Критический', 'kz': 'Шұғыл'},
        'шұғыл': {'ru': 'Критический', 'kz': 'Шұғыл'},
    }

    def match(risk):
        title_check = (risk.title_kz or risk.title or '').lower()
        if type and type not in title_check:
            return False

        dept_key = (risk.department or '').strip().lower()
        if department:
            for key, val in department_map.items():
                if key == dept_key:
                    if department.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        status_key = (risk.status or '').strip().lower()
        if status:
            for key, val in status_map.items():
                if key == status_key:
                    if status.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        priority_key = (risk.priority or '').strip().lower()
        if priority:
            for key, val in priority_map.items():
                if key == priority_key:
                    if priority.lower() != val.get(lang, '').lower():
                        return False
                    break
            else:
                return False

        if dateFrom and risk.created_at.strftime('%Y-%m-%d') < dateFrom:
            return False
        if dateTo and risk.created_at.strftime('%Y-%m-%d') > dateTo:
            return False

        return True

    filtered_risks = list(filter(match, risks))
    export_data = filtered_risks if any([type, department, status, priority, dateFrom, dateTo]) else risks

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)

    style = ParagraphStyle(name='Normal', fontName='Arial', fontSize=8, leading=10)

    data = [headings[lang]]
    for risk in export_data:
        priority_key = (risk.priority or '').strip().lower()
        status_key = (risk.status or '').strip().lower()
        dept_key = (risk.department or '').strip().lower()

        row = [
            f"RISK-{risk.id:03d}",
            department_map.get(dept_key, {}).get(lang, risk.department),
            risk.title_kz if lang == "kz" else risk.title,
            risk.likelihood,
            risk.impact,
            priority_map.get(priority_key, {}).get(lang, risk.priority),
            status_map.get(status_key, {}).get(lang, risk.status),
            risk.created_at.strftime("%Y-%m-%d %H:%M")
        ]
        data.append(row)

    wrapped_data = []
    for row in data:
        wrapped_row = [Paragraph(str(cell), style) for cell in row]
        wrapped_data.append(wrapped_row)

    table = Table(wrapped_data, colWidths=[50, 100, 120, 60, 60, 80, 80, 80], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), 
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('WORDWRAP', (0, 0), (-1, -1), 'CJK'), 
    ]))

    doc.build([table])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=risk_map_{lang}.pdf"}
    )

def normalize_department(value):
    key = value.lower().strip()
    return department_map.get(key, {}).get('ru', key)

def normalize_status(value):
    key = value.lower().strip()
    return status_map.get(key, {}).get('ru', key)




