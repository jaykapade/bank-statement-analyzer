from sqlalchemy import Column, String, Enum, Float, ForeignKey
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()


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
    filename = Column(String)
    status = Column(Enum(JobStatus), default=JobStatus.pending)


# -----------------------------
# Transaction Model
# -----------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.job_id"))

    date = Column(String)
    description = Column(String)
    amount = Column(Float)

    category = Column(String, nullable=True)
    category_status = Column(Enum(CategoryStatus), default=CategoryStatus.pending)
