from fastapi import APIRouter, HTTPException
import httpx
from sqlalchemy.orm import Session
from models import Asset
from database import get_db

router = APIRouter()

@router.post("/cmdb/import")
def import_from_cmdb(db: Session = Depends(get_db)):
    try:
        response = httpx.get("http://external-cmdb.local/api/assets") 
        response.raise_for_status()
        external_assets = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при подключении к CMDB: {e}")

    for item in external_assets:
        asset = db.query(Asset).filter(Asset.external_id == item["external_id"]).first()
        if asset:
            asset.name = item["name"]
            asset.type = item["type"]
            asset.criticality = item["criticality"]
            asset.owner = item["owner"]
        else:
                asset = Asset(
                name=item["name"],
                type=item["type"],
                criticality=item["criticality"],
                owner=item["owner"],
                external_id=item["external_id"],
                is_external=True
            )
            db.add(asset)
    db.commit()
    return {"status": "Импорт завершен", "count": len(external_assets)}
