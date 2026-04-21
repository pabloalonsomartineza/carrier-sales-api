from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True)
    mc_number = Column(String, nullable=True)
    carrier_name = Column(String, nullable=True)
    load_id = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    loadboard_rate = Column(Float, nullable=True)
    offered_rate = Column(Float, nullable=True)
    final_agreed_rate = Column(Float, nullable=True)
    negotiation_rounds = Column(Integer, default=0)
    outcome = Column(String, nullable=True)       # booked / no_deal / transferred / abandoned
    sentiment = Column(String, nullable=True)     # positive / neutral / negative
    fmcsa_verified = Column(String, nullable=True)  # verified / not_found / inactive
    call_duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
