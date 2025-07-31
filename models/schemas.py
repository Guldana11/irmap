from pydantic import BaseModel
from typing import Optional, List 
from datetime import datetime, date
from fastapi import Form


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

class RiskTypeOut(BaseModel):
    id: int
    title: str
    class Config:
        orm_mode = True

class MeasureOut(BaseModel):
    id: int
    title: str
    title_kz : Optional[str]= None
    risk_type_id: Optional[int]
    risk_type_name: Optional[str]
    responsible: Optional[str]
    due_date: Optional[date]
    description: Optional[str]
    status:str
    risk_type_name_kz: Optional[str]
    class Config:
        orm_mode = True

class MeasureCreate(BaseModel):
    id: Optional[int] = None
    title: str
    title_kz: str
    responsible: Optional[str] = None
    due_date: Optional[date] = None
    risk_type_id: int
    status: str
    description: Optional[str] = None

class MeasureUpdateSchema(BaseModel):
    responsible: Optional[str] = None
    due_date: Optional[date] = None
    status: str
    description: Optional[str] = None

class NotificationBase(BaseModel):
    id: int
    type: str
    measure_id: Optional[int] = None
    title: dict  
    message: dict 
    created_at: datetime
    read: bool

class NotificationOut(NotificationBase):
    pass