from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
import models 

DATABASE_URL = "postgresql://postgres:Monter69#@localhost:5432/irmap_pr"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    from models import user
    
    Base.metadata.create_all(bind=engine)
    
    return engine

if __name__ == "__main__":
    init_db()
    print("Database tables created successfully")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()