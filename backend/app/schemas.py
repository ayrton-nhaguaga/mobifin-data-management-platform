from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

Role = Literal['ADMIN', 'DATA_OWNER', 'DATA_STEWARD', 'DATA_ENGINEER', 'AUDITOR']
Classification = Literal['PÚBLICA', 'INTERNA', 'CONFIDENCIAL', 'RESTRITA']
Operation = Literal['DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class UserCreate(Input):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9_.-]+$')
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=12, max_length=128)
    role: Role


class UserUpdate(Input):
    role: Role
    active: bool


class PasswordChange(Input):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class ClientInput(Input):
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=150)
    document: str = Field(min_length=3, max_length=80)
    phone: str = Field(min_length=7, max_length=40, pattern=r'^\+?[0-9 ]+$')
    email: str | None = Field(default=None, max_length=150)
    birth_date: date | None = None
    address: str = Field(default='', max_length=200)
    source: str = Field(default='MANUAL', min_length=1, max_length=80)

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        if value and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Email inválido')
        return value or None

    @field_validator('birth_date')
    @classmethod
    def past_date(cls, value):
        if value and value > date.today():
            raise ValueError('Nascimento no futuro')
        return value


class TransactionInput(Input):
    external_id: str = Field(min_length=1, max_length=80)
    client_id: int = Field(gt=0)
    operation: Operation
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Literal['MZN', 'USD', 'ZAR', 'EUR'] = 'MZN'
    occurred_at: datetime
    status: Literal['COMPLETED', 'PENDING', 'CANCELLED'] = 'COMPLETED'
    source: str = Field(default='MANUAL', min_length=1, max_length=80)
    external_ref: str = Field(min_length=1, max_length=80)

    @field_validator('occurred_at')
    @classmethod
    def transaction_date(cls, value):
        from app.models import now
        if value.replace(tzinfo=None) > now().replace(tzinfo=None):
            raise ValueError('Data no futuro')
        return value


class RuleInput(Input):
    dataset: Literal['clients', 'transactions']
    name: str = Field(min_length=3, max_length=150)
    dimension: Literal['completeness', 'uniqueness', 'validity']
    kind: Literal['required', 'unique', 'email', 'positive', 'date', 'operation', 'reference', 'currency', 'phone', 'schema']
    field: str = Field(min_length=1, max_length=80)
    active: bool = True
    blocking: bool = True
    target: Decimal = Field(default=99, ge=0, le=100)


class Toggle(Input):
    active: bool


class PolicyInput(Input):
    name: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=10, max_length=10000)
    owner: str = Field(min_length=3, max_length=100)
    active: bool = True


class DatasetUpdate(Input):
    owner: str = Field(min_length=3, max_length=100)
    steward: str = Field(min_length=3, max_length=100)
    engineer: str = Field(min_length=3, max_length=100)
    auditor: str = Field(min_length=3, max_length=100)
    classification: Classification
    fields: list[dict]


class Correction(Input):
    data: dict[str, str]
    reason: str = Field(min_length=10, max_length=500)


class IncidentUpdate(Input):
    status: Literal['ASSIGNED', 'IN_PROGRESS', 'PENDING_VALIDATION', 'RESOLVED', 'CLOSED']
    assignee: str | None = None
    evidence: str | None = Field(default=None, max_length=2000)


class Execute(Input):
    batch_id: int = Field(gt=0)


class ReconciliationJustification(Input):
    currency: Literal['MZN', 'USD', 'ZAR', 'EUR']
    reason: str = Field(min_length=15, max_length=2000)
