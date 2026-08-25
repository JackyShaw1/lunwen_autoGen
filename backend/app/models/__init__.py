import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# SQLite 使用 JSON 类型
JSON = SQLiteJSON


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(String(20), default="teacher")
    quota_remaining: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cases: Mapped[list["CaseTask"]] = relationship(back_populates="user")


class SystemMeta(Base):
    """一次性数据迁移标记，防止服务重启时重复补发额度。"""

    __tablename__ = "system_meta"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseTask(Base):
    __tablename__ = "case_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(100))
    course_name: Mapped[str] = mapped_column(String(200), default="")
    case_type: Mapped[str] = mapped_column(String(50), default="决策型")
    difficulty: Mapped[str] = mapped_column(String(20), default="中级")
    target_audience: Mapped[str] = mapped_column(String(50), default="本科")
    target_words: Mapped[int] = mapped_column(Integer, default=2800)
    learning_objectives: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    workflow_template: Mapped[str] = mapped_column(String(50), default="sequential_standard")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="cases")
    packages: Mapped[list["CasePackage"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    agent_logs: Mapped[list["AgentRunLog"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    exports: Mapped[list["ExportRecord"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class CasePackage(Base):
    __tablename__ = "case_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("case_tasks.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    package: Mapped[dict] = mapped_column(JSON, default=dict)
    rubric_overall: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["CaseTask"] = relationship(back_populates="packages")


class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("case_tasks.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    round: Mapped[int] = mapped_column(Integer, default=0)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["CaseTask"] = relationship(back_populates="agent_logs")


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(20))
    config_yaml: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("case_tasks.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(10))
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["CaseTask"] = relationship(back_populates="exports")
