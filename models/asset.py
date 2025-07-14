from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    criticality = Column(String)
    owner = Column(String, nullable=True)
    department = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    external_id = Column(String, unique=True)
    is_external = Column(Boolean, default=False)
    source = Column(String, nullable=False)
    inventory_number = Column(Integer)
    description = Column(String)

    risk_assessments = relationship("RiskAssessment", back_populates="asset", cascade="all, delete")
