# routes/cmdb_import.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db
from models.asset import Asset
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GLPI_URL = os.getenv("GLPI_URL")
APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
USER_TOKEN = os.getenv("GLPI_USER_TOKEN")

DEVICE_TYPES = {
    "Computer": "Computer",
    "Monitor": "Monitor",
    "Printer": "Printer"
}

@router.post("/cmdb/import")
def import_from_glpi(db: Session = Depends(get_db)):
    if not all([GLPI_URL, APP_TOKEN, USER_TOKEN]):
        return {"error": "GLPI credentials are not configured in .env"}

    headers = {
        "App-Token": APP_TOKEN,
        "Authorization": f"user_token {USER_TOKEN}"
    }

    try:
        with httpx.Client() as client:
            # Init session
            auth_response = client.get(f"{GLPI_URL}/initSession", headers=headers)
            if auth_response.status_code != 200:
                return {"error": "GLPI session init failed", "details": auth_response.text}

            session_token = auth_response.json().get("session_token")
            if not session_token:
                return {"error": "No session token returned from GLPI"}

            session_headers = {
                "App-Token": APP_TOKEN,
                "Session-Token": session_token
            }

            total_received = 0
            new_assets = 0

            for glpi_type, asset_type in DEVICE_TYPES.items():
                response = client.get(f"{GLPI_URL}/{glpi_type}", headers=session_headers)
                if response.status_code != 200:
                    continue  # пропускаем неудачные запросы

                items = response.json()
                total_received += len(items)

                for item in items:
                    if not isinstance(item, dict) or "id" not in item:
                        continue

                    external_id = str(item["id"])
                    asset = db.query(Asset).filter_by(external_id=external_id).first()
                    if asset:
                        asset.name = item.get("name", asset.name)
                        asset.type = asset_type
                    else:
                        new_asset = Asset(
                            name=item.get("name", "Unnamed"),
                            type=asset_type,
                            criticality="medium",
                            external_id=external_id,
                            is_external=True
                        )
                        db.add(new_asset)
                        new_assets += 1

            client.get(f"{GLPI_URL}/killSession", headers=session_headers)

    except httpx.RequestError as e:
        return {"error": "HTTP connection failed", "details": str(e)}

    db.commit()
    return {
        "status": "Импорт завершен",
        "new_assets": new_assets,
        "total_received": total_received
    }
