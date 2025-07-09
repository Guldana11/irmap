from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    phone = Column(String)
    position = Column(String)
    two_fa_method = Column(String)
    password = Column(String, nullable=False)
    telegram_username = Column(String)
    telegram_chat_id = Column(String)
    totp_secret = Column(String)
    verification_code = Column(String)
    verified = Column(Boolean, default=False)
    email = Column(String, unique=True, nullable=False)
