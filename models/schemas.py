from pydantic import BaseModel
from typing import Optional, List 
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

    class Config:
        orm_mode = True

class AssetCreate(AssetBase):
    pass

class AssetUpdate(AssetBase):
    id: int

class AssetDelete(BaseModel):
    id: int

class RiskListEntryOut(BaseModel):
    id: int
    title: str
    title_kz: str
    likelihood: int
    impact: int
    priority: str
    status: str
    created_at: datetime
    department: str
    
    class Config:
        orm_mode = True

class RiskCreateSchema(BaseModel):
    title: str
    title_kz: str
    likelihood: int
    impact: int
    priority: str
    status: str
    department: str

    class Config:
        orm_mode = True

class RiskUpdateSchema(BaseModel):
      
    likelihood: int
    impact: int
    priority: str
    status: str
    
    class Config:
        orm_mode = True
    