"""
Spectr SQL Database Layer — PostgreSQL with SQLAlchemy Async.
Handles structured data: users, sessions, audit logs, billing, client ledgers.
MongoDB remains the primary store for documents, statutes, and conversation history.
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey,
    Index, Enum as SQLEnum, event, BigInteger
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from contextlib import asynccontextmanager

logger = logging.getLogger("spectr.db")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./spectr.db"  # Default to SQLite for dev; use PostgreSQL in production
)

# Production: postgresql+asyncpg://user:pass@host:5432/spectr_db
# Dev/Test:   sqlite+aiosqlite:///./spectr.db

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20 if "postgresql" in DATABASE_URL else 5,
    max_overflow=10 if "postgresql" in DATABASE_URL else 2,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def gen_id(prefix: str = "") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:16]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("usr"))
    firebase_uid = Column(String(128), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    picture = Column(Text, default="")
    role = Column(String(32), default="analyst")  # analyst, partner, admin
    firm_name = Column(String(255), default="")
    phone = Column(String(20), default="")
    bar_council_no = Column(String(50), default="")  # For advocates
    ca_membership_no = Column(String(50), default="")  # For CAs
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_hash = Column(String(255), nullable=True)  # For local auth (bcrypt)
    totp_secret = Column(String(64), nullable=True)  # 2FA TOTP secret (encrypted)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("sess"))
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, index=True)  # SHA-256 of JWT
    refresh_token_hash = Column(String(128), nullable=True, index=True)
    ip_address = Column(String(45), default="")
    user_agent = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_active", "user_id", "is_active"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # login, query, export, delete, etc.
    resource_type = Column(String(50), default="")  # matter, document, client, etc.
    resource_id = Column(String(64), default="")
    ip_address = Column(String(45), default="")
    user_agent = Column(Text, default="")
    details = Column(JSON, nullable=True)  # Additional context
    risk_level = Column(String(20), default="low")  # low, medium, high, critical
    created_at = Column(DateTime, default=utcnow, index=True)

    # No FK relationship — users may only exist in MongoDB

    __table_args__ = (
        Index("ix_audit_action_time", "action", "created_at"),
        Index("ix_audit_risk", "risk_level", "created_at"),
    )


class Client(Base):
    __tablename__ = "clients"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("cli"))
    user_id = Column(String(64), nullable=False, index=True)  # Owner (CA/Lawyer)
    name = Column(String(255), nullable=False)
    entity_type = Column(String(50), default="individual")  # individual, company, llp, huf, trust, aop
    pan = Column(String(10), default="")
    gstin = Column(String(15), default="")
    cin = Column(String(21), default="")
    email = Column(String(255), default="")
    phone = Column(String(20), default="")
    address = Column(Text, default="")
    state_code = Column(String(2), default="")
    jurisdiction = Column(String(100), default="")  # AO jurisdiction for IT
    ward_circle = Column(String(50), default="")
    status = Column(String(20), default="active")  # active, inactive, archived
    engagement_type = Column(String(50), default="retainer")  # retainer, project, advisory
    billing_rate_hourly = Column(Float, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    billing_entries = relationship("BillingEntry", back_populates="client", cascade="all, delete-orphan")
    conflicts = relationship("ConflictCheck", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_clients_user_status", "user_id", "status"),
        Index("ix_clients_pan", "pan"),
        Index("ix_clients_gstin", "gstin"),
    )


class BillingEntry(Base):
    __tablename__ = "billing_entries"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("bill"))
    client_id = Column(String(64), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    matter_id = Column(String(64), default="")
    description = Column(Text, nullable=False)
    hours = Column(Float, default=0)
    rate = Column(Float, default=0)
    amount = Column(Float, default=0)
    billing_date = Column(DateTime, default=utcnow)
    category = Column(String(50), default="advisory")  # advisory, drafting, filing, appearance, travel, misc
    status = Column(String(20), default="unbilled")  # unbilled, billed, paid, written_off
    invoice_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    client = relationship("Client", back_populates="billing_entries")

    __table_args__ = (
        Index("ix_billing_client_status", "client_id", "status"),
        Index("ix_billing_user_date", "user_id", "billing_date"),
    )


class ConflictCheck(Base):
    __tablename__ = "conflict_checks"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("cfl"))
    user_id = Column(String(64), nullable=False, index=True)
    client_id = Column(String(64), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    check_type = Column(String(50), default="new_engagement")  # new_engagement, opposing_party, related_matter
    party_name = Column(String(255), nullable=False)
    party_pan = Column(String(10), default="")
    result = Column(String(20), default="clear")  # clear, conflict, potential_conflict
    conflicting_client_id = Column(String(64), nullable=True)
    conflicting_matter_id = Column(String(64), nullable=True)
    details = Column(Text, default="")
    checked_at = Column(DateTime, default=utcnow)
    checked_by = Column(String(64), default="")

    client = relationship("Client", back_populates="conflicts")


class ComplianceDeadline(Base):
    __tablename__ = "compliance_deadlines"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("cdl"))
    user_id = Column(String(64), nullable=False, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    matter_id = Column(String(64), nullable=True)
    title = Column(String(255), nullable=False)
    deadline_type = Column(String(50), nullable=False)  # gstr3b, gstr1, itr, tds_return, roc, etc.
    due_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending, completed, overdue, waived
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    penalty_risk = Column(Float, default=0)  # Estimated penalty in INR
    notes = Column(Text, default="")
    reminder_sent = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_compliance_user_due", "user_id", "due_date"),
        Index("ix_compliance_status", "status", "due_date"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("key"))
    user_id = Column(String(64), nullable=False, index=True)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)  # SHA-256 hash of the key
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification (e.g., "sk_live_")
    name = Column(String(100), default="Default")
    scopes = Column(JSON, default=list)  # ["read", "write", "admin"]
    rate_limit = Column(Integer, default=100)  # Requests per minute
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class RateLimitRecord(Base):
    __tablename__ = "rate_limits"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, index=True)  # IP or user_id or API key
    endpoint = Column(String(255), default="")
    window_start = Column(DateTime, nullable=False)
    request_count = Column(Integer, default=1)
    blocked = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_ratelimit_key_window", "key", "window_start"),
    )


# ==================== DATABASE LIFECYCLE ====================

async def init_db():
    """Create all tables. Call on app startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQL database initialized — all tables created")


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
    logger.info("SQL database connections closed")


@asynccontextmanager
async def get_session():
    """Async context manager for database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ==================== HELPER FUNCTIONS ====================

async def log_audit(
    action: str,
    user_id: str = "",
    resource_type: str = "",
    resource_id: str = "",
    ip_address: str = "",
    user_agent: str = "",
    details: dict = None,
    risk_level: str = "low"
):
    """Write an audit log entry. Fire-and-forget safe."""
    try:
        async with get_session() as session:
            entry = AuditLog(
                user_id=user_id or None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                risk_level=risk_level,
            )
            session.add(entry)
    except Exception as e:
        logger.error(f"Audit log write failed: {e}")


async def check_conflict(user_id: str, party_name: str, party_pan: str = "") -> dict:
    """Check for conflicts of interest against existing client base."""
    from sqlalchemy import select, or_, func
    async with get_session() as session:
        # Search by name similarity and PAN match
        conditions = [
            func.lower(Client.name).contains(party_name.lower())
        ]
        if party_pan and len(party_pan) == 10:
            conditions.append(Client.pan == party_pan.upper())

        stmt = select(Client).where(
            Client.user_id == user_id,
            Client.status == "active",
            or_(*conditions)
        )
        result = await session.execute(stmt)
        matches = result.scalars().all()

        if not matches:
            return {"result": "clear", "conflicts": []}

        conflicts = []
        for m in matches:
            conflicts.append({
                "client_id": m.id,
                "client_name": m.name,
                "pan": m.pan,
                "match_type": "pan_match" if party_pan and m.pan == party_pan.upper() else "name_match",
            })

        return {
            "result": "conflict" if any(c["match_type"] == "pan_match" for c in conflicts) else "potential_conflict",
            "conflicts": conflicts,
        }


async def get_billing_summary(user_id: str, client_id: str = None, period_days: int = 30) -> dict:
    """Get billing summary for a user/client."""
    from sqlalchemy import select, func
    async with get_session() as session:
        cutoff = utcnow() - timedelta(days=period_days)
        conditions = [
            BillingEntry.user_id == user_id,
            BillingEntry.billing_date >= cutoff,
        ]
        if client_id:
            conditions.append(BillingEntry.client_id == client_id)

        stmt = select(
            func.count(BillingEntry.id).label("total_entries"),
            func.sum(BillingEntry.hours).label("total_hours"),
            func.sum(BillingEntry.amount).label("total_amount"),
        ).where(*conditions)

        result = await session.execute(stmt)
        row = result.one()

        # Breakdown by status
        status_stmt = select(
            BillingEntry.status,
            func.sum(BillingEntry.amount).label("amount"),
        ).where(*conditions).group_by(BillingEntry.status)
        status_result = await session.execute(status_stmt)
        status_breakdown = {r.status: float(r.amount or 0) for r in status_result}

        return {
            "period_days": period_days,
            "total_entries": row.total_entries or 0,
            "total_hours": float(row.total_hours or 0),
            "total_amount": float(row.total_amount or 0),
            "by_status": status_breakdown,
        }


async def get_overdue_compliance(user_id: str) -> list:
    """Get all overdue compliance deadlines."""
    from sqlalchemy import select
    async with get_session() as session:
        stmt = select(ComplianceDeadline).where(
            ComplianceDeadline.user_id == user_id,
            ComplianceDeadline.status == "pending",
            ComplianceDeadline.due_date < utcnow(),
        ).order_by(ComplianceDeadline.due_date)
        result = await session.execute(stmt)
        deadlines = result.scalars().all()
        return [{
            "id": d.id, "title": d.title, "deadline_type": d.deadline_type,
            "due_date": d.due_date.isoformat(), "priority": d.priority,
            "penalty_risk": d.penalty_risk, "client_id": d.client_id,
            "days_overdue": (utcnow() - d.due_date).days,
        } for d in deadlines]
