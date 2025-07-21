from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship

from db import Base 

class RiskListEntry(Base):
    __tablename__ = "risk_list_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)  
    title_kz = Column(String, nullable=False) 
    likelihood = Column(Integer, nullable=False)  
    impact = Column(Integer, nullable=False)     
    priority = Column(String, nullable=False)     
    status = Column(String, nullable=False)      
    created_at = Column(DateTime, default=datetime.utcnow) 
    department = Column(String, nullable=True)

