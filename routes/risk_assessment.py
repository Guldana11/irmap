from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import pandas as pd
import io
from reportlab.pdfgen import canvas
from db import get_db
from models.asset import Asset
from models.risk_assessment import RiskAssessment, ThreatLibrary
from fastapi.templating import Jinja2Templates
from dependencies.lang import get_lang
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from pytz import timezone
from pathlib import Path
import os
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf')) 
KZ_TIMEZONE = timezone("Asia/Almaty")  


@router.get("/risk-assessment", response_class=HTMLResponse)
async def risk_assessment_page(
    request: Request,
    db: Session = Depends(get_db),
    lang: str = Depends(get_lang)
    ):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if isinstance(user, str):
        user = {"username": user}

    assets = db.query(Asset).all()
    methods = ["ISO/IEC 27005", "NIST SP 800-30", "OCTAVE"]
    
    threats = db.query(ThreatLibrary).all()

    return templates.TemplateResponse(
        "risk_assessment.html",
        {
            "request": request,
            "user": user,
            "lang": lang,
            "assets": assets,
            "methods": methods,
            "threats": threats
        }
    )

@router.post("/risk-assessment/calculate", response_class=JSONResponse)
async def calculate_risk(
    asset_id: int = Form(...),
    method: str = Form(...),
    threat: str = Form(...),
    vulnerability: str = Form(...),
    likelihood: int = Form(...),
    impact: int = Form(...),
    db: Session = Depends(get_db)
    ):
    score = likelihood * impact
    
    if score >= 15:
        level = "Критический"
        recommendations = ["Немедленное устранение", "Остановка процесса"]
    elif score >= 10:
        level = "Высокий"
        recommendations = ["Плановое устранение", "Временные меры защиты"]
    elif score >= 5:
        level = "Средний" 
        recommendations = ["Мониторинг", "Плановые меры"]
    else:
        level = "Низкий"
        recommendations = ["Приемлемый риск", "Периодический контроль"]

    logger.info(">> Сохраняем оценку риска...")


    assessment = RiskAssessment(
        asset_id=asset_id,
        method=method,
        threat=threat,
        vulnerability=vulnerability,
        likelihood=likelihood,
        impact=impact,
        score=score,
        level=level,
        recommendations=recommendations,
        created_at=datetime.utcnow()
    )
    
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {
        "score": score,
        "level": level,
        "recommendations": ", ".join(recommendations),
        "message": "Оценка риска успешно сохранена"
    }
    
@router.get("/risk-assessment/history")
def risk_history(request: Request, lang: str = "ru", db: Session = Depends(get_db)):
    assessments = db.query(RiskAssessment).all()

    threats = db.query(ThreatLibrary).all()
    threat_dict = {t.name: {"ru": t.name_ru, "kz": t.name_kz} for t in threats}

    for a in assessments:
        threat_info = threat_dict.get(a.threat, {"ru": a.threat, "kz": a.threat})
        a.threat_ru = threat_info["ru"]
        a.threat_kz = threat_info["kz"]

    return templates.TemplateResponse("risk_history.html", {
        "request": request,
        "assessments": assessments,
        "lang": lang,
    })

@router.get("/risk-assessment/export/excel")
async def export_excel(db: Session = Depends(get_db)):
    assessments = (
        db.query(RiskAssessment)
        .options(joinedload(RiskAssessment.asset))
        .order_by(RiskAssessment.created_at.desc())
        .all()
    )

    data = [
        {
            "ID": a.id,
            "Method": a.method,
            "Asset": a.asset.name,
            "Threat": a.threat,
            "Vulnerability": a.vulnerability,
            "Likelihood": a.likelihood,
            "Impact": a.impact,
            "Score": a.score,
            "Level": a.level,
            "Date": a.created_at.strftime("%Y-%m-%d %H:%M")
        } for a in assessments
    ]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Risk History', index=False)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=risk_history.xlsx"}
    )

@router.get("/risk-assessment/export/pdf")
async def export_pdf(lang: str = "ru", db: Session = Depends(get_db)):
    assessments = db.query(RiskAssessment).options(joinedload(RiskAssessment.asset)).all()

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)

    style = ParagraphStyle(
        name='Normal',
        fontName='Arial',
        fontSize=8,
        leading=10
    )

    headings = {
        "ru": ["ID", "Метод", "Актив", "Угроза", "Уязвимость", "Вероятность", "Воздействие", "Баллы", "Уровень", "Дата"],
        "kz": ["ID", "Әдіс", "Актив", "Қауіп", "Әлсіздік", "Ықтималдық", "Әсер ету", "Ұпай", "Деңгейі", "Күні"]
    }

    data = [headings.get(lang, headings["ru"])]
    for a in assessments:
        row = [
            a.id,
            a.method,
            Paragraph(a.asset.name, style),
            Paragraph(a.threat, style),
            Paragraph(a.vulnerability, style),
            a.likelihood,
            a.impact,
            a.score,
            {"Низкий": "Төмен", "Средний": "Орташа", "Высокий": "Жоғары", "Критический": "Сындарлы"}.get(a.level, a.level) if lang == "kz" else a.level,
            a.created_at.strftime('%Y-%m-%d %H:%M')
        ]
        data.append(row)

    col_widths = [25, 60, 80, 100, 100, 60, 60, 40, 60, 75]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
    ]))

    doc.build([table])
    output.seek(0)

    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=risk_assessments_{lang}.pdf"
    })

@router.post("/threats/import")
async def import_threats_from_local_json(
    request: Request,
    db: Session = Depends(get_db)
    ):
    BASE_DIR = Path(os.getcwd())
    file_path = BASE_DIR / "enterprise-attack_translated.json"
    print("📂 BASE_DIR:", BASE_DIR)
    print("📄 Ожидаемый путь файла:", file_path)
    print("✅ Файл существует?", file_path.exists())

    if not file_path.exists():
        return {"error": "Файл enterprise-attack_translated.json не найден"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            threats = json.load(f)

        imported = 0

        for threat in threats:
            name = threat.get("name")
            name_ru = threat.get("name_ru", name)
            name_kz = threat.get("name_kz", name)
            description = threat.get("description")
            description_ru = threat.get("description_ru", description)
            description_kz = threat.get("description_kz", description)
            external_refs = threat.get("external_references", [])
            mitre_id = ""

            for ref in external_refs:
                if ref.get("source_name") == "mitre-attack":
                    mitre_id = ref.get("external_id", "")
                    break


            if not name or not mitre_id:
                continue

            exists = db.query(ThreatLibrary).filter(ThreatLibrary.name == name).first()
            if exists:
                continue

            new_threat = ThreatLibrary(
                name=name,
                name_ru=name_ru,
                name_kz=name_kz,
                description=description,
                description_ru=description_ru,
                description_kz=description_kz,
                category="MITRE ATT&CK",
                severity="medium",
                common_controls=[]
            )
            db.add(new_threat)
            imported += 1

        db.commit()
        print(f"✅ Импортировано {imported} угроз.")
        return RedirectResponse(url="/risk-assessment", status_code=303)

    except Exception as e:
        return {"error": "Импорт из attack_patterns_slim_translated.json не удался", "details": str(e)}
