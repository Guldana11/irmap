from sqlalchemy import create_engine, Column, Integer, String, Date, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import date
import json

DATABASE_URL = "postgresql://postgres:Monter69#@localhost:5432/irmap_pr"
JSON_PATH = "C:/Users/nur03/Downloads/measures_data_120.json"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class Measure(Base):
    __tablename__ = "measures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    title_kz = Column(String, nullable=False)
    responsible = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, default="new")
    risk_type_id = Column(Integer, ForeignKey("risk_list_entries.id"))
    risk_type = relationship("RiskListEntry", backref="measures")

with open(JSON_PATH, "r", encoding="utf-8") as file:
    measures_data = json.load(file)

for m in measures_data:
    measure = Measure(
        title=m["title"],
        title_kz=m["title_kz"],
        responsible=m["responsible"],
        due_date=date.fromisoformat(m["due_date"]),
        description=m["description"],
        status=m["status"],
        risk_type_id=m["risk_type_id"]
    )
    session.add(measure)

session.commit()
session.close()
print("✅ Данные успешно загружены в таблицу measures.")
