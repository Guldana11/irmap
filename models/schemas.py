from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssetBase(BaseModel):
    name: str
    type: str
    criticality: str
    department: str
    owner: str
    status: str
    source: str
    created_at: Optional[datetime] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(AssetBase):
    id: int

class AssetDelete(BaseModel):
    id: int
