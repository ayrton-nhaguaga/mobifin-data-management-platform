import csv
import hashlib
import io
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from app.core.config import settings
from app.core.db import get_db
from app.core.security import current_user, allow, WRITERS, hasher, verify, token, audit
from app.models import *
from app.schemas import *
from app.quality import validate, FIELDS, REQUIRED, TARGETS, metric, assert_rule
from app.etl import execute
from app.lineage import node, edge

app = FastAPI(title='MobiFin Data Management Platform', version='1.0.0', description='ISUTC · Engenharia de Dados · Dados exclusivamente sintéticos')
app.add_middleware(CORSMiddleware, allow_origins=settings().cors_origins.split(','), allow_methods=['GET','POST','PATCH','PUT'], allow_headers=['Authorization','Content-Type'])


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc):
    return JSONResponse(status_code=409, content={'detail': 'Conflito de integridade: identificador duplicado ou referência inválida. Nenhuma alteração foi aplicada.'})


def record(obj, user=None):
    values = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs if c.key != 'password_hash'}
    if isinstance(obj, Client) and user and user.role in ('AUDITOR', 'DATA_OWNER'):
        for key in ('document', 'phone', 'email', 'birth_date', 'address'):
            values[key] = '••••' if values.get(key) else None
    return jsonable_encoder(values, custom_encoder={Decimal: str})


def required(db, model, id):
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(404, 'Registo não encontrado')
    return obj


def page(db, model, query=None, user=None, offset=0, limit=50):
    query = query if query is not None else select(model)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(model.id.desc()).offset(offset).limit(limit)).all()
    return {'items': [record(x, user) for x in items], 'total': total, 'offset': offset, 'limit': limit}


@app.get('/api/health')
def health(db=Depends(get_db)):
    db.execute(select(1))
    return {'status': 'ok', 'service': 'MobiFin'}


@app.post('/api/auth/token')
def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    recent = db.scalar(select(func.count()).select_from(Audit).where(Audit.username == form.username, Audit.action == 'LOGIN', Audit.result == 'FAILURE', Audit.created_at > now()-timedelta(minutes=5)))
    if recent >= 10:
        raise HTTPException(429, 'Demasiadas tentativas; aguarde cinco minutos')
    if not user or not user.active or not verify(form.password, user.password_hash):
        audit(db, form.username[:80], 'LOGIN', 'user', result='FAILURE')
        db.commit()
        raise HTTPException(401, 'Credenciais inválidas')
    audit(db, user, 'LOGIN', 'user', user.id)
    db.commit()
    return {'access_token': token(user), 'token_type': 'bearer', 'user': record(user)}


@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return record(user)


@app.post('/api/auth/logout')
def logout(user=Depends(current_user), db=Depends(get_db)):
    user.token_version += 1
    audit(db, user, 'LOGOUT', 'user', user.id)
    db.commit()
    return {'message': 'Sessões revogadas'}


@app.post('/api/auth/password')
def password(data: PasswordChange, user=Depends(current_user), db=Depends(get_db)):
    if not verify(data.current_password, user.password_hash):
        raise HTTPException(400, 'Palavra-passe actual incorrecta')
    user.password_hash = hasher.hash(data.new_password)
    user.token_version += 1
    audit(db, user, 'PASSWORD_CHANGE', 'user', user.id)
    db.commit()
    return {'message': 'Palavra-passe alterada; inicie sessão novamente'}


@app.get('/api/users')
def users(user=Depends(allow('ADMIN')), db=Depends(get_db)):
    return page(db, User)


@app.post('/api/users', status_code=201)
def create_user(data: UserCreate, user=Depends(allow('ADMIN')), db=Depends(get_db)):
    values = data.model_dump(exclude={'password'})
    item = User(**values, password_hash=hasher.hash(data.password))
    db.add(item)
    db.flush()
    audit(db, user, 'CREATE_USER', 'user', item.id, role=item.role)
    db.commit()
    return record(item)


@app.patch('/api/users/{id}')
def update_user(id: int, data: UserUpdate, user=Depends(allow('ADMIN')), db=Depends(get_db)):
    item = required(db, User, id)
    if item.id == user.id:
        raise HTTPException(409, 'Não pode alterar o próprio perfil ou desactivar a própria conta')
    item.role, item.active = data.role, data.active
    item.token_version += 1
    audit(db, user, 'UPDATE_USER', 'user', id, **data.model_dump())
    db.commit()
    return record(item)


@app.get('/api/clients')
def clients(q: str = '', source: str = '', offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), user=Depends(current_user), db=Depends(get_db)):
    stmt = select(Client)
    if q:
        stmt = stmt.where(or_(Client.name.ilike(f'%{q}%'), Client.external_id.ilike(f'%{q}%')))
    if source:
        stmt = stmt.where(Client.source == source)
    return page(db, Client, stmt, user, offset, limit)


@app.get('/api/clients/{id}')
def client(id: int, user=Depends(current_user), db=Depends(get_db)):
    return record(required(db, Client, id), user)


@app.post('/api/clients', status_code=201)
def create_client(data: ClientInput, user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    item = Client(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, 'CREATE_CLIENT', 'client', item.id)
    db.commit()
    return record(item, user)


@app.put('/api/clients/{id}')
def update_client(id: int, data: ClientInput, user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    item = required(db, Client, id)
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    dim = db.scalar(select(DimClient).where(DimClient.client_id == id))
    if dim:
        dim.name, dim.location = item.name, item.address
    audit(db, user, 'UPDATE_CLIENT', 'client', id)
    db.commit()
    return record(item, user)


@app.get('/api/transactions')
def transactions(q: str = '', currency: str = '', operation: str = '', status: str = '', offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), user=Depends(current_user), db=Depends(get_db)):
    stmt = select(Transaction)
    if q:
        stmt = stmt.where(or_(Transaction.external_id.ilike(f'%{q}%'), Transaction.external_ref.ilike(f'%{q}%')))
    for column, value in [(Transaction.currency, currency), (Transaction.operation, operation), (Transaction.status, status)]:
        if value:
            stmt = stmt.where(column == value)
    return page(db, Transaction, stmt, user, offset, limit)


@app.get('/api/transactions/{id}')
def transaction(id: int, user=Depends(current_user), db=Depends(get_db)):
    return record(required(db, Transaction, id), user)


@app.post('/api/transactions', status_code=201)
def create_transaction(data: TransactionInput, user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    required(db, Client, data.client_id)
    item = Transaction(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, 'CREATE_TRANSACTION', 'transaction', item.id)
    db.commit()
    return record(item)


@app.put('/api/transactions/{id}')
def update_transaction(id: int, data: TransactionInput, user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    item = required(db, Transaction, id)
    if db.scalar(select(Fact.id).where(Fact.transaction_id == id)):
        raise HTTPException(409, 'Transacção consolidada é imutável; use uma operação compensatória')
    required(db, Client, data.client_id)
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, 'UPDATE_TRANSACTION', 'transaction', id)
    db.commit()
    return record(item)


@app.post('/api/imports/{dataset}', status_code=201)
async def import_csv(dataset: Literal['clients', 'transactions'], file: UploadFile = File(...), user=Depends(allow('ADMIN','DATA_ENGINEER')), db=Depends(get_db)):
    content = await file.read(settings().upload_limit + 1)
    if len(content) > settings().upload_limit:
        raise HTTPException(413, 'Ficheiro excede o limite de 10 MiB')
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(422, 'Seleccione um ficheiro CSV UTF-8')
    checksum = hashlib.sha256(content).hexdigest()
    previous = db.scalar(select(Batch).where(Batch.dataset == dataset, Batch.checksum == checksum))
    if previous:
        return record(previous)
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not set(REQUIRED[dataset]).issubset(headers) or set(headers) - set(FIELDS[dataset]):
            raise ValueError('Cabeçalhos inválidos; consulte o modelo CSV')
        rows = list(reader)
        if not rows or len(rows) > 50000 or any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ValueError('CSV vazio, excede 50 000 linhas ou possui colunas inconsistentes')
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(422, str(exc))
    batch = Batch(dataset=dataset, filename=Path(file.filename).name[:200], checksum=checksum, row_count=len(rows))
    db.add(batch)
    db.flush()
    for number, data in enumerate(rows, 2):
        db.add(StageRow(batch_id=batch.id, row_number=number, original=data, data={k: v.strip() for k, v in data.items()}))
    node(db, batch, f'source:{batch.id}', batch.filename, 'SOURCE', f'SHA256 {checksum}')
    node(db, batch, f'staging:{batch.id}', f'Staging #{batch.id}', 'STAGING', f'{len(rows)} linhas; original preservado')
    edge(db, f'source:{batch.id}', f'staging:{batch.id}', 'Extracção CSV UTF-8')
    audit(db, user, 'IMPORT_CSV', 'batch', batch.id, rows=len(rows), checksum=checksum)
    db.commit()
    return record(batch)


@app.get('/api/batches')
def batches(user=Depends(current_user), db=Depends(get_db)):
    return page(db, Batch, limit=200)


@app.get('/api/batches/{id}/rows')
def batch_rows(id: int, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    return page(db, StageRow, select(StageRow).where(StageRow.batch_id == id), offset=offset, limit=limit)


@app.patch('/api/staging/{id}')
def correct_row(id: int, data: Correction, user=Depends(allow('ADMIN', 'DATA_STEWARD')), db=Depends(get_db)):
    row = required(db, StageRow, id)
    batch = db.scalar(select(Batch).where(Batch.id == row.batch_id).with_for_update())
    if row.loaded:
        raise HTTPException(409, 'Linha já carregada; corrija na origem operacional')
    if set(data.data) - set(FIELDS[batch.dataset]) or any(len(v) > 500 for v in data.data.values()):
        raise HTTPException(422, 'Campos desconhecidos ou demasiado longos')
    row.data = dict(row.data, **data.data)
    batch.revision += 1
    batch.status = 'CORRECTED'
    audit(db, user, 'CORRECT_STAGE', 'row', id, fields=list(data.data), reason=data.reason, revision=batch.revision)
    db.commit()
    return record(row)


@app.get('/api/rules')
def rules(user=Depends(current_user), db=Depends(get_db)):
    return page(db, Rule, limit=200)


@app.post('/api/rules', status_code=201)
def create_rule(data: RuleInput, user=Depends(allow('ADMIN','DATA_STEWARD')), db=Depends(get_db)):
    assert_rule(data)
    item = Rule(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, 'CREATE_RULE', 'rule', item.id)
    db.commit()
    return record(item)


@app.patch('/api/rules/{id}')
def toggle_rule(id: int, data: Toggle, user=Depends(allow('ADMIN','DATA_STEWARD')), db=Depends(get_db)):
    rule = required(db, Rule, id)
    rule.active = data.active
    audit(db, user, 'TOGGLE_RULE', 'rule', id, active=data.active)
    db.commit()
    return record(rule)


@app.post('/api/validations')
def run_validation(data: Execute, user=Depends(allow(*WRITERS)), db=Depends(get_db)):
    batch = db.scalar(select(Batch).where(Batch.id == data.batch_id).with_for_update())
    if not batch:
        raise HTTPException(404, 'Lote não encontrado')
    run = validate(db, batch)
    audit(db, user, 'VALIDATE', 'batch', batch.id, run_id=run.id)
    db.commit()
    return record(run)


@app.get('/api/validations')
def validations(batch_id: int | None = None, user=Depends(current_user), db=Depends(get_db)):
    stmt = select(ValidationRun)
    if batch_id:
        stmt = stmt.where(ValidationRun.batch_id == batch_id)
    return page(db, ValidationRun, stmt, limit=200)


@app.get('/api/violations')
def violations(run_id: int | None = None, dimension: str = '', offset: int = Query(0, ge=0), user=Depends(current_user), db=Depends(get_db)):
    stmt = select(Violation)
    if run_id:
        stmt = stmt.where(Violation.run_id == run_id)
    if dimension:
        stmt = stmt.where(Violation.dimension == dimension)
    return page(db, Violation, stmt, offset=offset)


@app.post('/api/etl')
def run_etl(data: Execute, user=Depends(allow('ADMIN','DATA_ENGINEER')), db=Depends(get_db)):
    result = execute(db, required(db, Batch, data.batch_id))
    audit(db, user, 'EXECUTE_ETL', 'etl', result.id)
    db.commit()
    return record(result)


@app.get('/api/etl')
def etl_runs(user=Depends(current_user), db=Depends(get_db)):
    return page(db, ETLRun, limit=200)


@app.post('/api/etl/retry')
def retry_etl(data: Execute, user=Depends(allow('ADMIN','DATA_ENGINEER')), db=Depends(get_db)):
    batch = db.scalar(select(Batch).where(Batch.id == data.batch_id).with_for_update())
    if not batch:
        raise HTTPException(404, 'Lote não encontrado')
    pending = db.scalar(select(func.count()).select_from(StageRow).where(StageRow.batch_id == batch.id, StageRow.loaded.is_(False)))
    if not pending:
        raise HTTPException(409, 'Não existem linhas pendentes para reprocessar')
    batch.revision += 1
    result = execute(db, batch)
    audit(db, user, 'RETRY_ETL', 'etl', result.id, pending=pending, revision=batch.revision)
    db.commit()
    return record(result)


@app.post('/api/etl/{id}/reconcile')
def reconcile(id: int, user=Depends(allow('ADMIN','DATA_ENGINEER','AUDITOR')), db=Depends(get_db)):
    run = required(db, ETLRun, id)
    totals = {currency: amount for currency, amount in db.execute(select(Fact.currency, func.sum(Fact.amount)).where(Fact.etl_id == id).group_by(Fact.currency))}
    previous = {e['currency']: e for e in run.reconciliation}
    entries = []
    for currency in sorted(set(previous) | set(totals)):
        original = previous.get(currency, {})
        source = Decimal(original.get('source', '0'))
        warehouse = totals.get(currency, Decimal('0.00'))
        difference = source - warehouse
        same_difference = difference == Decimal(original.get('difference', '0'))
        entry = {'currency':currency, 'source':str(source), 'warehouse':str(warehouse), 'difference':str(difference),
                 'justification':original.get('justification') if same_difference else None}
        if same_difference and original.get('justified_by'):
            entry.update(justified_by=original['justified_by'], justified_at=original['justified_at'])
        entries.append(entry)
    run.reconciliation = entries
    audit(db, user, 'RECONCILE', 'etl', id, differences=sum(Decimal(e['difference']) != 0 for e in entries))
    db.commit()
    return record(run)


@app.post('/api/etl/{id}/justify')
def justify(id: int, data: ReconciliationJustification, user=Depends(allow('ADMIN','DATA_OWNER')), db=Depends(get_db)):
    run = required(db, ETLRun, id)
    entries = [dict(e) for e in run.reconciliation]
    entry = next((e for e in entries if e['currency'] == data.currency), None)
    if not entry or Decimal(entry['difference']) == 0:
        raise HTTPException(409, 'Não existe diferença financeira não nula nesta moeda')
    entry.update(justification=data.reason, justified_by=user.username, justified_at=now().isoformat())
    run.reconciliation = entries
    audit(db, user, 'JUSTIFY_DIFFERENCE', 'etl', id, currency=data.currency, reason=data.reason)
    db.commit()
    return record(run)


@app.get('/api/catalog')
def catalog(user=Depends(current_user), db=Depends(get_db)):
    items = []
    for dataset in db.scalars(select(Dataset)):
        values = record(dataset)
        values['rules'] = list(db.scalars(select(Rule.id).where(Rule.dataset == dataset.name)))
        values['etl_runs'] = list(db.scalars(select(ETLRun.id).join(Batch).where(Batch.dataset == dataset.name).order_by(ETLRun.id.desc()).limit(20)))
        items.append(values)
    return {'items': items, 'total': len(items)}


@app.put('/api/catalog/{id}')
def update_dataset(id: int, data: DatasetUpdate, user=Depends(allow('ADMIN','DATA_OWNER')), db=Depends(get_db)):
    item = required(db, Dataset, id)
    for field in data.fields:
        if set(field) != {'name','type','classification'} or field['classification'] not in ('PÚBLICA','INTERNA','CONFIDENCIAL','RESTRITA'):
            raise HTTPException(422, 'Metadados de campo inválidos')
    # Seeded PII remains restricted; changing a label cannot grant access to raw values.
    for field in data.fields:
        if field['name'] in ('document','phone','email','birth_date') and field['classification'] != 'RESTRITA':
            raise HTTPException(422, 'Campos pessoais mantêm classificação RESTRITA')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    item.updated_at = now()
    audit(db, user, 'UPDATE_CATALOG', 'dataset', id)
    db.commit()
    return record(item)


@app.get('/api/policies')
def policies(user=Depends(current_user), db=Depends(get_db)):
    return page(db, Policy)


@app.post('/api/policies', status_code=201)
def create_policy(data: PolicyInput, user=Depends(allow('ADMIN','DATA_OWNER')), db=Depends(get_db)):
    item = Policy(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, 'CREATE_POLICY', 'policy', item.id)
    db.commit()
    return record(item)


@app.put('/api/policies/{id}')
def update_policy(id: int, data: PolicyInput, user=Depends(allow('ADMIN','DATA_OWNER')), db=Depends(get_db)):
    item = required(db, Policy, id)
    item.history = item.history + [{'version': item.version, 'name': item.name, 'content': item.content, 'owner': item.owner, 'active': item.active, 'at': now().isoformat(), 'by': user.username}]
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    item.version += 1
    item.updated_at = now()
    audit(db, user, 'UPDATE_POLICY', 'policy', id, version=item.version)
    db.commit()
    return record(item)


@app.get('/api/incidents')
def incidents(status: str = '', offset: int = Query(0, ge=0), user=Depends(current_user), db=Depends(get_db)):
    stmt = select(Incident)
    if status:
        stmt = stmt.where(Incident.status == status)
    return page(db, Incident, stmt, offset=offset)


@app.patch('/api/incidents/{id}')
def update_incident(id: int, data: IncidentUpdate, user=Depends(allow('ADMIN','DATA_STEWARD')), db=Depends(get_db)):
    item = required(db, Incident, id)
    transitions = {'OPEN': ['ASSIGNED'], 'ASSIGNED': ['IN_PROGRESS'], 'IN_PROGRESS': ['PENDING_VALIDATION'], 'PENDING_VALIDATION': ['RESOLVED','IN_PROGRESS'], 'RESOLVED': ['CLOSED']}
    if data.status not in transitions.get(item.status, []):
        raise HTTPException(409, 'Transição de estado inválida')
    if data.status == 'ASSIGNED':
        assignee = db.scalar(select(User).where(User.username == data.assignee, User.active.is_(True), User.role.in_(WRITERS)))
        if not assignee:
            raise HTTPException(422, 'Atribua um utilizador activo com perfil técnico')
        item.assignee = assignee.username
    if data.evidence:
        item.evidence = data.evidence
    if data.status in ('RESOLVED','CLOSED'):
        row = required(db, StageRow, item.row_id)
        batch = required(db, Batch, row.batch_id)
        latest = db.scalar(select(ValidationRun).where(ValidationRun.batch_id == batch.id).order_by(ValidationRun.id.desc()))
        rule = required(db, Rule, item.rule_id)
        if not latest or latest.revision != batch.revision or not rule.active or not any(r['id'] == rule.id for r in latest.rule_snapshot) or not item.evidence:
            raise HTTPException(409, 'Exige evidência e validação actual com a regra activa')
        violation = db.scalar(select(Violation.id).where(Violation.run_id == latest.id, Violation.row_id == row.id, Violation.rule_id == item.rule_id))
        if violation:
            raise HTTPException(409, 'A regra continua a falhar; corrija e revalide')
        item.validated_run_id = latest.id
    item.status = data.status
    item.history = item.history + [{'status': data.status, 'at': now().isoformat(), 'by': user.username, 'evidence': item.evidence, 'validated_run_id': item.validated_run_id}]
    audit(db, user, 'UPDATE_INCIDENT', 'incident', id, status=item.status)
    db.commit()
    return record(item)


@app.get('/api/audit')
def audit_events(action: str = '', offset: int = Query(0, ge=0), user=Depends(allow('ADMIN','AUDITOR')), db=Depends(get_db)):
    stmt = select(Audit)
    if action:
        stmt = stmt.where(Audit.action == action)
    return page(db, Audit, stmt, offset=offset)


@app.get('/api/lineage')
def lineage(batch_id: int | None = None, transaction_id: int | None = None, user=Depends(current_user), db=Depends(get_db)):
    trace = None
    if transaction_id:
        fact = db.scalar(select(Fact).where(Fact.transaction_id == transaction_id))
        if not fact:
            raise HTTPException(404, 'Transacção ainda não consolidada por um lote ETL')
        run = required(db, ETLRun, fact.etl_id)
        batch_id = run.batch_id
        row = required(db, StageRow, fact.row_id)
        trace = {'transaction_id': transaction_id, 'source_identifier': row.data.get('external_id'), 'source_row': row.row_number,
                 'batch_id': batch_id, 'etl_id': run.id, 'validation_id': run.validation_id, 'fact_id': fact.id,
                 'report_node': f'report:{run.id}', 'transformations': ['strip whitespace', 'Decimal(18,2)', 'dimensional keys', 'COMPLETED eligibility']}
    stmt = select(LineageNode)
    if batch_id:
        stmt = stmt.where(LineageNode.batch_id == batch_id)
    else:
        latest = db.scalar(select(Batch.id).order_by(Batch.id.desc()).limit(1))
        stmt = stmt.where(LineageNode.batch_id == latest)
    nodes = list(db.scalars(stmt))
    ids = [n.id for n in nodes]
    edges = list(db.scalars(select(LineageEdge).where(LineageEdge.source.in_(ids), LineageEdge.target.in_(ids))))
    return {'nodes': [record(n) for n in nodes], 'edges': [record(e) for e in edges], 'trace': trace}


def reports_data(db):
    daily = db.execute(select(DimTime.day_date, Fact.currency, func.sum(Fact.amount), func.count(Fact.id)).join(DimTime, Fact.time_sk == DimTime.id).group_by(DimTime.day_date, Fact.currency).order_by(DimTime.day_date)).all()
    monthly = db.execute(select(DimTime.year, DimTime.month, Fact.currency, func.sum(Fact.amount), func.count(Fact.id)).join(DimTime, Fact.time_sk == DimTime.id).group_by(DimTime.year, DimTime.month, Fact.currency).order_by(DimTime.year, DimTime.month)).all()
    operations = db.execute(select(DimOperation.code, Fact.currency, func.sum(Fact.amount), func.count(Fact.id)).join(DimOperation, Fact.operation_sk == DimOperation.id).group_by(DimOperation.code, Fact.currency)).all()
    return {'daily': [{'day': str(day), 'currency': c, 'volume': str(v), 'quantity': n} for day,c,v,n in daily],
            'monthly': [{'month': f'{year}-{month:02d}', 'currency': c, 'volume': str(v), 'quantity': n} for year,month,c,v,n in monthly],
            'operations': [{'operation': op, 'currency': c, 'volume': str(v), 'quantity': n} for op,c,v,n in operations],
            'reconciliation': [dict(run_id=r.id, batch_id=r.batch_id, entries=r.reconciliation) for r in db.scalars(select(ETLRun).order_by(ETLRun.id.desc()).limit(100))]}


@app.get('/api/reports')
def reports(user=Depends(current_user), db=Depends(get_db)):
    return reports_data(db)


@app.get('/api/dashboard')
def dashboard(user=Depends(current_user), db=Depends(get_db)):
    # Latest validation per batch avoids counting corrected revisions twice.
    latest_ids = select(func.max(ValidationRun.id)).group_by(ValidationRun.batch_id)
    latest = list(db.scalars(select(ValidationRun).where(ValidationRun.id.in_(latest_ids))))
    metrics = {}
    for dimension in ('completeness', 'uniqueness', 'validity'):
        denominator = sum(r.metrics[dimension]['denominator'] for r in latest)
        passed = sum(r.metrics[dimension]['passed'] for r in latest)
        metrics[dimension] = metric(passed, denominator, TARGETS[dimension], 'rule_value_checks' if dimension == 'validity' else 'records')
    runs = list(db.scalars(select(ETLRun)))
    delivery = [r for r in runs if r.on_time is not None]
    metrics['timeliness'] = metric(sum(r.on_time for r in delivery), len(delivery), 99, 'report_deliveries')
    differences = [entry for r in runs for entry in r.reconciliation if Decimal(entry['difference']) != 0]
    metrics['consistency'] = metric(sum(bool(e['justification']) for e in differences), len(differences), 100, 'financial_differences')
    metrics['consistency']['reconciliations'] = sum(len(r.reconciliation) for r in runs)
    metrics['consistency']['unexplained_differences'] = sum(not e['justification'] for e in differences)
    distribution = [{'status': status, 'count': count} for status,count in db.execute(select(Incident.status, func.count()).group_by(Incident.status))]
    history = list(db.scalars(select(ValidationRun).order_by(ValidationRun.id.desc()).limit(20)))
    return {'clients': db.scalar(select(func.count()).select_from(Client)), 'transactions': db.scalar(select(func.count()).select_from(Transaction)),
            'facts': db.scalar(select(func.count()).select_from(Fact)), 'metrics': metrics,
            'open_incidents': db.scalar(select(func.count()).select_from(Incident).where(Incident.status.not_in(['RESOLVED','CLOSED']))),
            'last_etl': record(runs[-1]) if runs else None, 'incident_distribution': distribution,
            'quality_history': [record(r) for r in reversed(history)], 'daily': reports_data(db)['daily']}
