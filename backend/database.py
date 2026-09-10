import json
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_image = Column(String(500), nullable=False)
    preprocessed_image = Column(String(500), nullable=False)
    overall_score = Column(Float, nullable=False, default=0.0)
    compliance_status = Column(String(50), nullable=False, default="NON_COMPLIANT")
    total_passed = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_needs_review = Column(Integer, default=0)
    extracted_fields = Column(Text, nullable=False, default="{}")
    evaluation_results = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "original_image": self.original_image,
            "preprocessed_image": self.preprocessed_image,
            "overall_score": round(self.overall_score, 1),
            "compliance_status": self.compliance_status,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_needs_review": self.total_needs_review,
            "extracted_fields": json.loads(self.extracted_fields) if self.extracted_fields else {},
            "evaluation_results": json.loads(self.evaluation_results) if self.evaluation_results else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
