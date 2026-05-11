"""SQLAlchemy models for persisted APES audit runs."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from backend.app.db.engine import Base


class Audit(Base):
    """Master record for one audit run."""

    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, unique=True, nullable=False)
    shop_url = Column(Text, nullable=False)
    store_name = Column(Text)
    status = Column(Text, default="pending", nullable=False)
    before_score = Column(Integer)
    after_score = Column(Integer)
    total_queries = Column(Integer, default=20)
    failed_queries = Column(Integer, default=0)
    high_impact_fixes = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))


class StoreContext(Base):
    """Full crawled store context for one audit."""

    __tablename__ = "store_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False)
    store_data = Column(JSONB, nullable=False)
    gaps_detected = Column(JSONB, default=list, nullable=False)
    crawl_coverage = Column(JSONB, default=dict, nullable=False)
    product_count = Column(Integer, default=0)
    has_policies = Column(Boolean, default=False)
    has_faqs = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class PersonaQuery(Base):
    """Generated customer query for one audit."""

    __tablename__ = "persona_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False)
    query_id = Column(Text, nullable=False)
    persona = Column(Text, nullable=False)
    category = Column(Text)
    query = Column(Text, nullable=False)
    intent = Column(Text)
    dimension = Column(Text, nullable=False)
    difficulty = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_query_audit", "audit_id", "query_id", unique=True),)


class Simulation(Base):
    """Before and after simulated shopping-agent answer for a query."""

    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False)
    query_id = Column(Text, nullable=False)
    persona = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    dimension = Column(Text, nullable=False)
    response = Column(Text)
    classification = Column(Text)
    confidence = Column(Float)
    severity = Column(Text)
    hedging_detected = Column(Boolean, default=False)
    refusal_detected = Column(Boolean, default=False)
    is_grounded = Column(Boolean, default=True)
    ungrounded_claims = Column(JSONB, default=list)
    fixed_context = Column(Boolean, default=False)
    after_response = Column(Text)
    after_classification = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_sim_audit", "audit_id", "query_id", unique=True),)


class Finding(Base):
    """Forensic root cause for a failed query."""

    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False)
    query_id = Column(Text, nullable=False)
    gap_type = Column(Text, nullable=False)
    specific_issue = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    impact_on_conversion = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_finding_audit", "audit_id", "query_id", unique=True),)


class Fix(Base):
    """Generated content improvement for a finding."""

    __tablename__ = "fixes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False)
    query_id = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    original_content = Column(Text)
    improved_content = Column(Text)
    changes_made = Column(JSONB, default=list)
    confidence_improvement_reason = Column(Text)
    impact_points = Column(Integer, default=0)
    applied = Column(Boolean, default=False)
    applied_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_fix_audit", "audit_id", "query_id", unique=True),)


class ScoreReport(Base):
    """Before/after score report for one audit."""

    __tablename__ = "score_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(Text, ForeignKey("audits.audit_id", ondelete="CASCADE"), nullable=False, unique=True)
    before_score = Column(Integer, nullable=False)
    after_score = Column(Integer, nullable=False)
    delta = Column(Integer, nullable=False)
    before_dimensions = Column(JSONB, nullable=False)
    after_dimensions = Column(JSONB, nullable=False)
    action_plan = Column(JSONB, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
