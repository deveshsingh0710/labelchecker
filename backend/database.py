import json
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def hash_password(password: str) -> str:
    """Deterministic salted SHA256 hash for demo-grade auth."""
    salt = "labelcheck_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    # Organization type enum: brand | government | marketplace | audit_firm
    type = Column(String(50), nullable=False, default="brand")
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="organization")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    role = Column(String(50), default="member")  # admin | inspector | member
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name if self.organization else None,
            "organization_type": self.organization.type if self.organization else None,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    organization_name = Column(String(255), nullable=False)
    organization_type = Column(String(50), nullable=False)  # brand | government | marketplace | audit_firm
    message = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending | contacted | closed
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "organization_name": self.organization_name,
            "organization_type": self.organization_type,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
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

    organization = relationship("Organization", back_populates="verifications")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
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


# Seeded demo organization IDs for deterministic 1-click tenant switching
DEMO_ORG_BRAND_ID = "org-demo-brand-himalayan"
DEMO_ORG_GOVT_ID = "org-demo-govt-delhi"
DEMO_ORG_MARKETPLACE_ID = "org-demo-mkt-quickcart"


def init_db():
    """Initializes tables, handles SQLite column migrations, and seeds demo tenants."""
    Base.metadata.create_all(bind=engine)

    # SQLite migration: add organization_id to verifications if table already existed
    with engine.connect() as conn:
        try:
            cols_res = conn.execute(text("PRAGMA table_info(verifications)"))
            cols = [row[1] for row in cols_res.fetchall()]
            if "organization_id" not in cols:
                conn.execute(text("ALTER TABLE verifications ADD COLUMN organization_id VARCHAR(36)"))
                conn.commit()
        except Exception:
            pass

    # Seed default demo organizations and demo users
    db = SessionLocal()
    try:
        demo_orgs = [
            {
                "id": DEMO_ORG_BRAND_ID,
                "name": "Himalayan Naturals FMCG",
                "type": "brand",
                "user_email": "compliance@himalayannaturals.in",
                "user_name": "Aarav Sharma (Brand Manager)",
                "role": "admin"
            },
            {
                "id": DEMO_ORG_GOVT_ID,
                "name": "Dept of Legal Metrology (Delhi HQ)",
                "type": "government",
                "user_email": "inspector.delhi@legalmetrology.gov.in",
                "user_name": "Rajesh Kumar (Senior Inspector)",
                "role": "inspector"
            },
            {
                "id": DEMO_ORG_MARKETPLACE_ID,
                "name": "QuickCart Marketplace",
                "type": "marketplace",
                "user_email": "seller-ops@quickcart.com",
                "user_name": "Priya Verma (Listing Compliance Lead)",
                "role": "admin"
            }
        ]

        for item in demo_orgs:
            org = db.query(Organization).filter(Organization.id == item["id"]).first()
            if not org:
                org = Organization(
                    id=item["id"],
                    name=item["name"],
                    type=item["type"]
                )
                db.add(org)
                db.flush()

            user = db.query(User).filter(User.email == item["user_email"]).first()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    email=item["user_email"],
                    password_hash=hash_password("demo1234"),
                    name=item["user_name"],
                    organization_id=org.id,
                    role=item["role"]
                )
                db.add(user)

        # Backfill any existing unassociated verifications to the primary demo brand
        db.query(Verification).filter(Verification.organization_id == None).update(
            {"organization_id": DEMO_ORG_BRAND_ID}
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
