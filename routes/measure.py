from fastapi import APIRouter, Depends, Form, UploadFile, File, Request, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from db import get_db
from models.measure import Measure, Notification
from models.schemas import MeasureOut, RiskTypeOut, NotificationBase, NotificationOut, MeasureCreate, MeasureUpdateSchema
from datetime import date, datetime, timedelta
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from dependencies.lang import get_lang
from models.risk_map import RiskListEntry
import pandas as pd
from io import BytesIO


app = FastAPI()

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/measure")
def measure_page(request: Request, 
    db: Session = Depends(get_db),
    lang: str = Depends(get_lang)
    ):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if isinstance(user, str):
        user = {"username": user}

    all_risks = db.query(RiskListEntry).all()
    seen_titles = set()
    unique_risk_types = []
    for rt in all_risks:
        if rt.title not in seen_titles:
            seen_titles.add(rt.title)
            unique_risk_types.append(rt)

    measures = db.query(Measure).all()

    return templates.TemplateResponse("measure.html", {
        "request": request,
        "user": user,
        "risk_types": unique_risk_types,
        "measures": measures,  
        "lang": lang 
        })
app.include_router(router)

@router.get("/measure/list", response_model=List[MeasureOut])
def list_measures(db: Session = Depends(get_db)):
    measures = db.query(Measure).all()
    return [
        MeasureOut(
            id=m.id,
            title=m.title,
            title_kz=m.title_kz,
            risk_type_id=m.risk_type_id,
            risk_type_name=m.risk_type.title if m.risk_type else None,
            risk_type_name_kz=m.risk_type.title_kz if m.risk_type_kz else None,
            responsible=m.responsible,
            due_date=m.due_date,
            description=m.description,
            status=m.status
        )
        for m in measures
    ]

@router.post("/measure/create")
def create_measure(data: MeasureCreate, db: Session = Depends(get_db)):   
    measure = Measure(
        title=data.title,
        title_kz=data.title_kz,
        risk_type_id=data.risk_type_id,
        responsible=data.responsible,
        due_date=data.due_date,
        description=data.description,
        status=data.status,
    )
    db.add(measure)
    db.commit()
    db.refresh(measure)
    return {"message": "Создано"}

@router.put("/measure/update/{id}")
async def update_measure(id: int, measure_data: MeasureUpdateSchema, db: Session = Depends(get_db)):
    measure = db.query(Measure).filter_by(id=id).first()
    if not measure:
        raise HTTPException(status_code=404, detail="Мера не найдена")

    if measure_data.responsible is not None:
        measure.responsible = measure_data.responsible

    if measure_data.due_date is not None:
        measure.due_date = measure_data.due_date

    if measure_data.status:
        measure.status = measure_data.status

    if measure_data.description is not None:
        measure.description = measure_data.description

    db.commit()
    return {"message": "Мера успешно обновлена"}
    
@router.get("/risk-types/list", response_model=List[RiskTypeOut])
def get_risk_types(db: Session = Depends(get_db)):
    return db.query(RiskType).all()

@router.delete("/measure/delete/{id}")
def delete_measure(id: int, db: Session = Depends(get_db)):
    measure = db.query(Measure).filter_by(id=id).first()
    if not measure:
        raise HTTPException(status_code=404, detail="Мера не найдена")

    db.delete(measure)
    db.commit()
    return {"message": "Мера удалена"}

@router.get("/measure/export/excel")
def export_measures_excel(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_type_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    ):
    query = db.query(Measure).options(joinedload(Measure.risk_type))

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            (Measure.title.ilike(search_lower)) |
            (Measure.title_kz.ilike(search_lower)) |
            (Measure.responsible.ilike(search_lower))
        )
    if status:
        query = query.filter(Measure.status.ilike(status))
    if risk_type_id:
        query = query.filter(Measure.risk_type_id == risk_type_id)
    if date_from:
        query = query.filter(Measure.due_date >= date_from)
    if date_to:
        query = query.filter(Measure.due_date <= date_to)

    measures = query.all()

    data = [{
        "Название": m.title,
        "Название (каз)": m.title_kz,
        "Тип риска": m.risk_type.title if m.risk_type else "",
        "Тип риска (каз)": m.risk_type.title_kz if m.risk_type else "",
        "Ответственный": m.responsible,
        "Статус": m.status,
        "Срок": m.due_date.strftime("%Y-%m-%d") if m.due_date else ""
    } for m in measures]

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Measures")

    output.seek(0)
    filename = f"measures_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )    

@router.get("/measure/notifications", response_model=List[NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    lang: str = Query("ru", regex="^(ru|kz)$")
    ):
    current_date = datetime.utcnow().date()
    seven_days_ago = current_date - timedelta(days=7)
    three_days_later = current_date + timedelta(days=3)

    all_notifications = db.query(Notification).order_by(Notification.created_at.desc()).all()

    def to_output(notification: Notification):
        return {
            "id": notification.id,
            "type": notification.type,
            "measure_id": notification.measure_id,
            "title": {"ru": notification.title_ru, "kz": notification.title_kz},
            "message": {"ru": notification.message_ru, "kz": notification.message_kz},
            "created_at": notification.created_at,
            "read": notification.read
        }

    return [to_output(n) for n in all_notifications]


    new_notifications = []

    overdue_measures = db.query(Measure).filter(
        Measure.due_date < current_date,
        ~Measure.status.in_(["завершена", "completed", "аяқталған"])
    ).all()
    for measure in overdue_measures:
        new_notifications.append(Notification(
            type="overdue",
            measure_id=measure.id,
            title_ru="Просроченная мера",
            title_kz="Кешіктірілген шара",
            message_ru=f'Мера "{measure.title}" просрочена (до {measure.due_date})',
            message_kz=f'"{measure.title_kz or measure.title}" шарасы кешіктірілді ({measure.due_date} дейін)',
            read=False
        ))

    upcoming_measures = db.query(Measure).filter(
        Measure.due_date >= current_date,
        Measure.due_date <= three_days_later,
        ~Measure.status.in_(["завершена", "completed", "аяқталған"])
    ).all()
    for measure in upcoming_measures:
        days_left = (measure.due_date - current_date).days
        new_notifications.append(Notification(
            type="upcoming",
            measure_id=measure.id,
            title_ru="Приближается срок",
            title_kz="Мерзім жақындап жатыр",
            message_ru=f'Мера "{measure.title}" истекает через {days_left} {get_day_word(days_left, "ru")} (до {measure.due_date})',
            message_kz=f'"{measure.title_kz or measure.title}" шарасы {days_left} {get_day_word(days_left, "kz")} ішінде аяқталуы керек ({measure.due_date} дейін)',
            read=False
        ))

    new_measures_count = db.query(Measure).filter(
        Measure.created_at >= seven_days_ago
    ).count()
    if new_measures_count > 0:
        new_notifications.append(Notification(
            type="new",
            measure_id=None,
            title_ru="Новые меры",
            title_kz="Жаңа шаралар",
            message_ru=f"За последние 7 дней добавлено {new_measures_count} новых мер",
            message_kz=f"Соңғы 7 күнде {new_measures_count} жаңа шара қосылды",
            read=False
        ))

    no_responsible_measures = db.query(Measure).filter(
        Measure.responsible == None
    ).all()
    for measure in no_responsible_measures:
        new_notifications.append(Notification(
            type="no_responsible",
            measure_id=measure.id,
            title_ru="Нет ответственного",
            title_kz="Жауапты жоқ",
            message_ru=f'Мера "{measure.title}" не имеет назначенного ответственного',
            message_kz=f'"{measure.title_kz or measure.title}" шарасына жауапты тағайындалмаған',
            read=False
        ))

    stale_measures = db.query(Measure).filter(
        Measure.status.in_(["новая", "new", "жаңа"]),
        Measure.created_at <= seven_days_ago
    ).all()
    for measure in stale_measures:
        days_in_status = (current_date - measure.created_at.date()).days
        new_notifications.append(Notification(
            type="stale",
            measure_id=measure.id,
            title_ru="Долго в статусе 'Новая'",
            title_kz="'Жаңа' статусында ұзақ уақыт",
            message_ru=f'Мера "{measure.title}" уже {days_in_status} дней в статусе "Новая"',
            message_kz=f'"{measure.title_kz or measure.title}" шарасы "Жаңа" статусында {days_in_status} күн болды',
            read=False
        ))

    for n in new_notifications:
        db.add(n)
    db.commit()

    return [to_output(n) for n in new_notifications]

@router.post("/measure/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    
    notification.read = True
    db.commit()
    
    return {"message": "Уведомление помечено как прочитанное"}

@router.post("/measure/notifications/mark-all-read")
def mark_all_notifications_as_read(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.read == False).update({"read": True})
    db.commit()
    
    return {"message": "Все уведомления помечены как прочитанные"}

def get_day_word(n, lang):
    if lang == "ru":
        if 11 <= n % 100 <= 14:
            return "дней"
        elif n % 10 == 1:
            return "день"
        elif 2 <= n % 10 <= 4:
            return "дня"
        else:
            return "дней"
    elif lang == "kz":
        return "күн"  
    return "дней"
