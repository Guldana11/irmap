import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:Monter69#@localhost:5432/irmap_pr"
JSON_PATH = "C:/Users/nur03/Downloads/risk_data_120.json"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

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

with open(JSON_PATH, "r", encoding="utf-8") as file:
    risks = json.load(file)

for r in risks:
    entry = RiskListEntry(
        title=r["title"],
        title_kz=r["title_kz"],
        likelihood=r["likelihood"],
        impact=r["impact"],
        priority=r["priority"],
        status=r["status"],
        department=r["department"],
        created_at=datetime.fromisoformat(r["created_at"])
    )
    session.add(entry)

session.commit()
session.close()

print("✅ Данные успешно загружены в risk_list_entries.")
