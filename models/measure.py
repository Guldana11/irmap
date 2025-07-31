from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime

class Measure(Base):
    __tablename__ = "measures"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    title_kz = Column(String, nullable=False)
    responsible = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 
    risk_type_id = Column(Integer, ForeignKey("risk_list_entries.id"))
    risk_type = relationship("RiskListEntry")
    risk_type_kz = relationship("RiskListEntry")
    notifications = relationship("Notification", back_populates="measure")


class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  
    measure_id = Column(Integer, ForeignKey('measures.id'), nullable=True)
    title_ru = Column(String)
    title_kz = Column(String)
    message_ru = Column(String)
    message_kz = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
    
    measure = relationship("Measure", back_populates="notifications")
