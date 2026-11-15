import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from fastapi import HTTPException
from app.models import Rule, StageRow, ValidationRun, Violation, Incident, Client, Transaction, now
from app.lineage import node, edge
from app.schemas import ClientInput, TransactionInput
from pydantic import ValidationError

TARGETS = {'completeness': 98, 'uniqueness': 99, 'validity': 99.5, 'timeliness': 99, 'consistency': 100}
FIELDS = {
    'clients': ['external_id', 'name', 'document', 'phone', 'email', 'birth_date', 'address', 'source'],
    'transactions': ['external_id', 'client_external_id', 'operation', 'amount', 'currency', 'occurred_at', 'status', 'source', 'external_ref'],
}
REQUIRED = {'clients': ['external_id', 'name', 'document', 'phone', 'source'],
            'transactions': FIELDS['transactions']}


def parse_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)


def metric(passed, total, target, unit='records'):
    return {'passed': passed, 'denominator': total, 'percentage': round(passed * 100 / total, 4) if total else None,
            'target': target, 'unit': unit}


def validate(db, batch):
    rows = list(db.scalars(select(StageRow).where(StageRow.batch_id == batch.id).order_by(StageRow.row_number)))
    rules = list(db.scalars(select(Rule).where(Rule.dataset == batch.dataset, Rule.active.is_(True))))
    clients = {c.external_id for c in db.scalars(select(Client))}
    documents = {c.document: c.external_id for c in db.scalars(select(Client))}
    existing_clients = {c.external_id for c in db.scalars(select(Client))}
    txs = list(db.scalars(select(Transaction)))
    existing_tx = {t.external_id for t in txs}
    existing_refs = {(t.source, t.external_ref) for t in txs}
    counts = {}
    for r in rules:
        if r.kind == 'unique':
            counts[r.id] = Counter((x.data.get('source', ''), x.data.get(r.field, '')) if r.field == 'external_ref'
                                   else x.data.get(r.field, '') for x in rows)
    failures, invalid_rows = [], set()
    dimension_bad = {'completeness': set(), 'uniqueness': set()}
    validity_total = validity_bad = 0
    for row in rows:
        for rule in rules:
            value = str(row.data.get(rule.field, '')).strip()
            bad = False
            try:
                if rule.kind == 'required':
                    bad = not value
                elif rule.kind == 'unique':
                    key = (row.data.get('source', ''), value) if rule.field == 'external_ref' else value
                    bad = bool(value) and counts[rule.id][key] > 1
                    if not row.loaded:
                        if batch.dataset == 'clients':
                            bad |= value in (existing_clients if rule.field == 'external_id' else documents)
                        elif rule.field == 'external_id':
                            bad |= value in existing_tx
                        else:
                            bad |= key in existing_refs
                elif rule.kind == 'email':
                    bad = bool(value) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) is None
                elif rule.kind == 'positive':
                    amount = Decimal(value)
                    bad = not amount.is_finite() or amount <= 0 or amount >= Decimal('10000000000000000') or amount.as_tuple().exponent < -2
                elif rule.kind == 'date':
                    bad = bool(value) and parse_date(value) > now()
                elif rule.kind == 'operation':
                    bad = value not in ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT')
                elif rule.kind == 'currency':
                    bad = value not in ('MZN', 'USD', 'ZAR', 'EUR')
                elif rule.kind == 'reference':
                    bad = value not in clients
                elif rule.kind == 'phone':
                    bad = re.fullmatch(r'\+?[0-9 ]{7,40}', value) is None
                elif rule.kind == 'schema':
                    if batch.dataset == 'clients':
                        values = {k: v for k, v in row.data.items() if k in ClientInput.model_fields}
                        values['birth_date'] = values.get('birth_date') or None
                        values['email'] = values.get('email') or None
                        ClientInput(**values)
                    else:
                        values = {k: v for k, v in row.data.items() if k in TransactionInput.model_fields}
                        values['client_id'] = 1
                        TransactionInput(**values)
            except ValidationError:
                bad = True
            except (ValueError, InvalidOperation, TypeError):
                bad = True
            if rule.dimension == 'validity':
                validity_total += 1
                validity_bad += int(bad)
            if bad:
                failures.append((row, rule))
                if rule.blocking:
                    invalid_rows.add(row.id)
                if rule.dimension in dimension_bad:
                    dimension_bad[rule.dimension].add(row.id)
    metrics = {d: metric(len(rows) - len(bad), len(rows), TARGETS[d]) if any(r.dimension == d for r in rules) else metric(0, 0, TARGETS[d]) for d, bad in dimension_bad.items()}
    metrics['validity'] = metric(validity_total - validity_bad, validity_total, TARGETS['validity'], 'rule_value_checks')
    run = ValidationRun(batch_id=batch.id, revision=batch.revision, evaluated=len(rows), rejected=len(invalid_rows), metrics=metrics,
                        rule_snapshot=[{'id': r.id, 'name': r.name, 'dimension': r.dimension, 'kind': r.kind, 'field': r.field, 'blocking': r.blocking,
                                        'result': metric(len(rows) - sum(rule.id == r.id for _, rule in failures), len(rows), float(r.target))} for r in rules])
    db.add(run)
    db.flush()
    incidents = {(i.row_id, i.rule_id): i for i in db.scalars(select(Incident).join(StageRow, StageRow.id == Incident.row_id).where(StageRow.batch_id == batch.id))}
    for row, rule in failures:
        db.add(Violation(run_id=run.id, row_id=row.id, rule_id=rule.id, dimension=rule.dimension, message=rule.name))
        existing = incidents.get((row.id, rule.id))
        if not existing:
            incident = Incident(title=rule.name, description=f'Lote {batch.id}, linha {row.row_number}: {rule.field}',
                                row_id=row.id, rule_id=rule.id, due_at=now() + timedelta(days=2),
                                history=[{'status': 'OPEN', 'at': now().isoformat(), 'run_id': run.id}])
            db.add(incident)
            incidents[(row.id, rule.id)] = incident
        elif existing.status in ('RESOLVED', 'CLOSED'):
            existing.status = 'OPEN'
            existing.validated_run_id = None
            existing.history = existing.history + [{'status': 'OPEN', 'at': now().isoformat(), 'run_id': run.id}]
    batch.status = 'VALIDATED'
    key = f'validation:{run.id}'
    node(db, batch, key, f'Validação #{run.id}', 'VALIDATION', f'{len(rows)} linhas; {len(invalid_rows)} rejeitadas', 'WARNING' if invalid_rows else 'SUCCESS')
    edge(db, f'staging:{batch.id}', key, f'Revisão {batch.revision}; regras em snapshot')
    return run


def assert_rule(rule):
    dimensions = {'required': 'completeness', 'unique': 'uniqueness'}
    if rule.field not in FIELDS[rule.dataset] or rule.dimension != dimensions.get(rule.kind, 'validity'):
        raise HTTPException(422, 'Campo ou dimensão incompatível com a regra')
    permitted = {'unique': ['external_id', 'document'] if rule.dataset == 'clients' else ['external_id', 'external_ref'],
                 'reference': ['client_external_id'], 'positive': ['amount'], 'date': ['birth_date', 'occurred_at'],
                 'email': ['email'], 'phone': ['phone'], 'currency': ['currency'], 'operation': ['operation']}
    if rule.kind in permitted and rule.field not in permitted[rule.kind]:
        raise HTTPException(422, 'Tipo de regra incompatível com o campo')
