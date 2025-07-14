from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from sqlalchemy.orm import Session
from db import get_db
from models.asset import Asset
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
import io
import pandas as pd
from routes.cmdb_import import import_from_glpi
from starlette.status import HTTP_302_FOUND
from fastapi.templating import Jinja2Templates
from models.schemas import AssetCreate, AssetUpdate, AssetDelete
from typing import Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from fastapi import status as http_status
from fastapi.responses import Response
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import matplotlib.pyplot as plt
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import matplotlib.pyplot as plt
from io import BytesIO
from dependencies.lang import get_lang

pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf')) 

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/assets")
async def list_assets(
    request: Request,
    db: Session = Depends(get_db),
    lang: str = Depends(get_lang),
    page: int = 1,
    per_page: int = 10,
    search: str = "",
    type: str = "",
    criticality: str = ""
     ):
    offset = (page - 1) * per_page
    query = db.query(Asset)

    if search:
        query = query.filter(Asset.name.ilike(f"%{search}%"))
    if type:
        query = query.filter(Asset.type == type)
    if criticality:
        query = query.filter(Asset.criticality == criticality)

    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if isinstance(user, str):
        user = {"username": user}
    total_assets = query.count()
    assets = query.offset(offset).limit(per_page).all()
    total_pages = (total_assets + per_page - 1) // per_page

    return templates.TemplateResponse(
        "assets.html",
        {
            "request": request,
            "user":user,
            "lang": lang,
            "assets": assets,
            "total_assets": total_assets,
            "page": page,
            "total_pages": total_pages,
            "per_page": per_page,
            "search": search,
            "type": type,
            "criticality": criticality
        }
    )

@router.post("/assets/import")
def manual_import(request: Request, db: Session = Depends(get_db)):
    import_from_glpi(db)
    return RedirectResponse(url="/assets", status_code=HTTP_302_FOUND)

@router.post("/assets/create")
async def create_asset(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type: str = Form(...),
    criticality: str = Form(...),
    department: Optional[str] = Form(None),
    status: str = Form(...),
    inventory_number: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
    ):
    try:
        # Создаем новый актив
        new_asset = Asset(
            name=name,
            type=type,
            criticality=criticality,
            department=department,
            status=status,
            inventory_number=inventory_number,
            description=description,
            created_at=datetime.now()
        )
        
        db.add(new_asset)
        db.commit()
       
        return JSONResponse({
            "success": True,
            "message": "Актив успешно создан",
            "asset_id": new_asset.id
        })
    
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Ошибка при создании актива: {str(e)}"
        }, status_code=400)

@router.post("/assets/update")
async def update_asset(
    id: int = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    inventory_number: Optional[str] = Form(None),
    status: str = Form(...),
    criticality: str = Form(...),
    department: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
     ):
    try:        
        db_asset = db.query(Asset).filter(Asset.id == id).first()
        if not db_asset:
            return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Актив не найден"}
            )

        db_asset.name = name
        db_asset.type = type
        db_asset.criticality = criticality
        db_asset.department = department
        db_asset.status = status
        db_asset.inventory_number = inventory_number
        db_asset.owner = owner
        db_asset.source = source
        db_asset.description = description
        db_asset.updated_at = datetime.utcnow()

        db.commit()

        return RedirectResponse(url="/assets", status_code=http_status.HTTP_302_FOUND)

    except SQLAlchemyError as e:
        db.rollback()
        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Ошибка базы данных",
                "detail": str(e)
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Неизвестная ошибка",
                "detail": str(e)
            }
        )

@router.post("/assets/delete")
async def delete_asset(
    asset_data: AssetDelete,
    db: Session = Depends(get_db)
    ):
    try:
        db_asset = db.query(Asset).filter(Asset.id == asset_data.id).first()
        if not db_asset:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Актив не найден"}
            )

        db.delete(db_asset)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Актив успешно удален",
                "deleted_id": asset_data.id
            }
        )

    except SQLAlchemyError as e:
        db.rollback()
        return JSONResponse(
    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Ошибка базы данных",
                "detail": str(e)
            }
        )
    except Exception as e:
        return JSONResponse(
    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Неизвестная ошибка",
                "detail": str(e)
            }
        )

@router.get("/assets/export/excel")
async def export_assets_excel(
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db)
    ):
    # 🔍 Фильтрация по подразделению, если указано
    query = db.query(Asset)
    if department:
        query = query.filter(Asset.department == department)
    assets = query.all()
    
    # Далее всё без изменений...
    data = [{
        "Название": asset.name,
        "Тип": asset.type,
        "Критичность": asset.criticality,
        "Подразделение": asset.department or "",
        "Владелец": asset.owner or "",
        "Статус": asset.status,
        "Источник": asset.source,
        "Создан": asset.created_at.strftime("%d.%m.%Y") if asset.created_at else ""
    } for asset in assets]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='IT активы', index=False)
        worksheet = writer.sheets['IT активы']
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=it_assets.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    return StreamingResponse(output, headers=headers)

@router.get("/assets/export/pdf")
async def export_assets_pdf(department: str = Query("", alias="department"), db: Session = Depends(get_db)):
    query = db.query(Asset)
    if department:
        query = query.filter(Asset.department == department)
    assets = query.all()

    data = [[
        asset.name,
        asset.type,
        asset.criticality.capitalize() if asset.criticality else "-",
        asset.department or "-",
        asset.owner or "-",
        asset.status.capitalize() if asset.status else "-",
        asset.source or "-",
        asset.created_at.strftime("%d.%m.%Y") if asset.created_at else "-"
    ] for asset in assets]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))

    styles = getSampleStyleSheet()
    styles['Title'].fontName = 'Arial'
    styles['Normal'].fontName = 'Arial'

    elements = []
    title = Paragraph("Отчет по IT активам", styles['Title'])
    elements.append(title)

    headers = ["Название", "Тип", "Критичность", "Подразделение",
               "Владелец", "Статус", "Источник", "Создан"]
    table_data = [headers] + data
    table = Table(table_data)

    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    fig, ax = plt.subplots()
    types = [asset.type for asset in assets]
    ax.hist(types, bins=len(set(types)))
    ax.set_title("Распределение по типам")
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    plt.close()
    img_buffer.seek(0)

    img = Image(img_buffer, width=500, height=250)
    elements.append(img)

    doc.build(elements)
    buffer.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename=it_assets.pdf",
        "Content-Type": "application/pdf"
    }
    return Response(content=buffer.getvalue(), headers=headers)

@router.get("/assets/json")
async def get_all_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    return [
        {
            "name": asset.name,
            "type": asset.type,
            "criticality": asset.criticality,
            "status": asset.status,
            "department": asset.department or "Не указано"
        }
        for asset in assets
    ]
