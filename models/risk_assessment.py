from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base, engine  

Base.metadata.create_all(bind=engine)

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    method = Column(String, nullable=False)
    threat = Column(String, nullable=False)
    vulnerability = Column(String, nullable=False)
    likelihood = Column(Integer, nullable=False)
    impact = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    level = Column(String, nullable=False)
    recommendations = Column(JSON)  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    asset = relationship("Asset", back_populates="risk_assessments")

class ThreatLibrary(Base):
    __tablename__ = "threat_library"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    name_ru = Column(String, nullable=False)  
    name_kz = Column(String, nullable=False)  
    description = Column(String)
    description_ru = Column(String)
    description_kz = Column(String)
    category = Column(String)
    severity = Column(String)
    common_controls = Column(JSON)