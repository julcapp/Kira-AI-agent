from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

class Base(DeclarativeBase):
    pass

class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(100), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True) # task / idea
    title: Mapped[str] = mapped_column(String(500))
    agent: Mapped[str] = mapped_column(String(40), default="kiryusha")
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class InboxEvent(Base):
    __tablename__ = "inbox_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(200), unique=True)

class Conversation(Base):
    __tablename__ = "conversations"
    owner_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    selected_agent: Mapped[str] = mapped_column(String(40), default="kiryusha")

class VoicePreference(Base):
    __tablename__ = "voice_preferences"
    owner_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    mode: Mapped[str] = mapped_column(String(10), default="text")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(100), index=True)
    agent: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

def make_engine():
    if settings.database_url.startswith("sqlite:///"):
        from pathlib import Path
        filename = settings.database_url.removeprefix("sqlite:///")
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}, pool_pre_ping=True)

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    # Legacy MVP tables: knowledge_* tables are managed exclusively by Alembic.
    Base.metadata.create_all(engine, tables=[Record.__table__, InboxEvent.__table__,
                                            Conversation.__table__, VoicePreference.__table__,
                                            AuditLog.__table__])
