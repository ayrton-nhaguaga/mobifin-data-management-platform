from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'governance'}
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(default=0)


class Client(Base):
    __tablename__ = 'clients'
    __table_args__ = {'schema': 'operational'}
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    document: Mapped[str] = mapped_column(String(80), unique=True)
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(150))
    birth_date: Mapped[date | None]
    address: Mapped[str] = mapped_column(String(200), default='')
    source: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(default=now)


class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = (UniqueConstraint('source', 'external_ref'), CheckConstraint('amount > 0'), {'schema': 'operational'})
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('operational.clients.id'))
    operation: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default='MZN')
    occurred_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(20), default='COMPLETED')
    source: Mapped[str] = mapped_column(String(80))
    external_ref: Mapped[str] = mapped_column(String(80))


class Batch(Base):
    __tablename__ = 'batches'
    __table_args__ = (UniqueConstraint('dataset', 'checksum'), {'schema': 'staging'})
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(200))
    checksum: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int]
    revision: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default='IMPORTED')
    created_at: Mapped[datetime] = mapped_column(default=now)


class StageRow(Base):
    __tablename__ = 'rows'
    __table_args__ = (UniqueConstraint('batch_id', 'row_number'), {'schema': 'staging'})
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('staging.batches.id'))
    row_number: Mapped[int]
    original: Mapped[dict] = mapped_column(JSON)
    data: Mapped[dict] = mapped_column(JSON)
    loaded: Mapped[bool] = mapped_column(default=False)


class Rule(Base):
    __tablename__ = 'rules'
    __table_args__ = {'schema': 'quality'}
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    dimension: Mapped[str] = mapped_column(String(30))
    kind: Mapped[str] = mapped_column(String(30))
    field: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(default=True)
    blocking: Mapped[bool] = mapped_column(default=True)
    target: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=99)


class ValidationRun(Base):
    __tablename__ = 'validation_runs'
    __table_args__ = {'schema': 'quality'}
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('staging.batches.id'))
    revision: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)
    evaluated: Mapped[int]
    rejected: Mapped[int]
    metrics: Mapped[dict] = mapped_column(JSON)
    rule_snapshot: Mapped[list] = mapped_column(JSON)


class Violation(Base):
    __tablename__ = 'violations'
    __table_args__ = {'schema': 'quality'}
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('quality.validation_runs.id'))
    row_id: Mapped[int] = mapped_column(ForeignKey('staging.rows.id'))
    rule_id: Mapped[int] = mapped_column(ForeignKey('quality.rules.id'))
    dimension: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(250))


class ETLRun(Base):
    __tablename__ = 'etl_runs'
    __table_args__ = (UniqueConstraint('batch_id', 'revision'), {'schema': 'warehouse'})
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('staging.batches.id'))
    validation_id: Mapped[int] = mapped_column(ForeignKey('quality.validation_runs.id'))
    revision: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)
    finished_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(30), default='RUNNING')
    loaded: Mapped[int] = mapped_column(default=0)
    rejected: Mapped[int] = mapped_column(default=0)
    reconciliation: Mapped[list] = mapped_column(JSON, default=list)
    on_time: Mapped[bool | None]
    deadline: Mapped[datetime | None]


class DimClient(Base):
    __tablename__ = 'dim_cliente'
    __table_args__ = {'schema': 'warehouse'}
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('operational.clients.id'), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(200))


class DimTime(Base):
    __tablename__ = 'dim_tempo'
    __table_args__ = {'schema': 'warehouse'}
    id: Mapped[int] = mapped_column(primary_key=True)
    day_date: Mapped[date] = mapped_column(unique=True)
    day: Mapped[int]
    month: Mapped[int]
    year: Mapped[int]
    quarter: Mapped[int]


class DimOperation(Base):
    __tablename__ = 'dim_tipo_operacao'
    __table_args__ = {'schema': 'warehouse'}
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str] = mapped_column(String(100))


class Fact(Base):
    __tablename__ = 'fact_transaccao'
    __table_args__ = {'schema': 'warehouse'}
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey('operational.transactions.id'), unique=True)
    client_sk: Mapped[int] = mapped_column(ForeignKey('warehouse.dim_cliente.id'))
    time_sk: Mapped[int] = mapped_column(ForeignKey('warehouse.dim_tempo.id'))
    operation_sk: Mapped[int] = mapped_column(ForeignKey('warehouse.dim_tipo_operacao.id'))
    row_id: Mapped[int | None] = mapped_column(ForeignKey('staging.rows.id'), unique=True)
    etl_id: Mapped[int] = mapped_column(ForeignKey('warehouse.etl_runs.id'))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    quantity: Mapped[int] = mapped_column(default=1)


class Dataset(Base):
    __tablename__ = 'datasets'
    __table_args__ = {'schema': 'governance'}
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))
    owner: Mapped[str] = mapped_column(String(100))
    steward: Mapped[str] = mapped_column(String(100))
    engineer: Mapped[str] = mapped_column(String(100), default='engineer')
    auditor: Mapped[str] = mapped_column(String(100), default='auditor')
    classification: Mapped[str] = mapped_column(String(30))
    fields: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(default=now)


class Policy(Base):
    __tablename__ = 'policies'
    __table_args__ = {'schema': 'governance'}
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    content: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(default=1)
    active: Mapped[bool] = mapped_column(default=True)
    history: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(default=now)


class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = (UniqueConstraint('row_id', 'rule_id'), {'schema': 'quality'})
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    row_id: Mapped[int] = mapped_column(ForeignKey('staging.rows.id'))
    rule_id: Mapped[int] = mapped_column(ForeignKey('quality.rules.id'))
    severity: Mapped[str] = mapped_column(String(20), default='HIGH')
    assignee: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default='OPEN')
    created_at: Mapped[datetime] = mapped_column(default=now)
    due_at: Mapped[datetime]
    evidence: Mapped[str | None] = mapped_column(Text)
    validated_run_id: Mapped[int | None] = mapped_column(ForeignKey('quality.validation_runs.id'))
    history: Mapped[list] = mapped_column(JSON, default=list)


class LineageNode(Base):
    __tablename__ = 'lineage_nodes'
    __table_args__ = {'schema': 'governance'}
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('staging.batches.id'))
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(default=now)


class LineageEdge(Base):
    __tablename__ = 'lineage_edges'
    __table_args__ = {'schema': 'governance'}
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(ForeignKey('governance.lineage_nodes.id'))
    target: Mapped[str] = mapped_column(ForeignKey('governance.lineage_nodes.id'))
    description: Mapped[str] = mapped_column(String(250))


class Audit(Base):
    __tablename__ = 'events'
    __table_args__ = {'schema': 'audit'}
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(30), default='SUCCESS')
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now)
