from sqlalchemy import (
    Column,
    String,
    Enum,
    Numeric,
    ForeignKey,
    DateTime,
    MetaData,
    func,
)
from sqlalchemy.orm import declarative_base
import enum

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

Base = declarative_base(metadata=metadata)


# -----------------------------
# Job Status Enum
# -----------------------------
class JobStatus(str, enum.Enum):
    pending = "pending"
    extracting = "extracting"
    extracted = "extracted"
    categorizing = "categorizing"
    completed = "completed"
    extract_failed = "extract_failed"
    categorize_failed = "categorize_failed"
    failed = "failed"


# -----------------------------
# Category Status Enum
# -----------------------------
class CategoryStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


# -----------------------------
# Job Model
# -----------------------------
class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    filename = Column(String)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    s3_url = Column(String)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# -----------------------------
# Transaction Model
# -----------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.job_id"))

    date = Column(String)
    description = Column(String)
    amount = Column(Numeric(18, 2))

    category = Column(String, nullable=True)
    category_status = Column(Enum(CategoryStatus), default=CategoryStatus.pending)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# -----------------------------
# User Model
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)


# -----------------------------
# Session Model
# -----------------------------
class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
