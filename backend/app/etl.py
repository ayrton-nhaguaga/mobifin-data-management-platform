from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, insert, update
from fastapi import HTTPException
import pandas as pd
from pydantic import ValidationError
from app.models import (Batch, StageRow, ValidationRun, Violation, ETLRun, Client, Transaction,
                        DimClient, DimTime, DimOperation, Fact, Dataset, now)
from app.schemas import ClientInput, TransactionInput
from app.quality import validate, parse_date
from app.lineage import node, edge
from app.core.config import settings


def execute(db, batch):
    # Lock the batch in the same transaction as validation and loading (PostgreSQL).
    db.scalar(select(Batch).where(Batch.id == batch.id).with_for_update())
    previous = db.scalar(select(ETLRun).where(ETLRun.batch_id == batch.id, ETLRun.revision == batch.revision))
    if previous:
        return previous
    validation = validate(db, batch)
    blocking_rules = [r['id'] for r in validation.rule_snapshot if r['blocking']]
    blocked = set(db.scalars(select(Violation.row_id).where(Violation.run_id == validation.id, Violation.rule_id.in_(blocking_rules))))
    rows = list(db.scalars(select(StageRow).where(StageRow.batch_id == batch.id, StageRow.loaded.is_(False)).order_by(StageRow.row_number)))
    eligible = [r for r in rows if r.id not in blocked]
    run = ETLRun(batch_id=batch.id, validation_id=validation.id, revision=batch.revision, rejected=len(blocked))
    db.add(run)
    db.flush()
    frame = pd.DataFrame([dict(r.data, _row_id=r.id) for r in eligible]).fillna('')
    row_map = {r.id: r for r in eligible}
    source_totals, target_totals = {}, {}
    clients_by_external = {c.external_id: c for c in db.scalars(select(Client))}
    prepared = []
    for record in frame.to_dict(orient='records'):
        row = row_map[record.pop('_row_id')]
        try:
            if batch.dataset == 'clients':
                cleaned = {k: v for k, v in record.items() if k in ClientInput.model_fields}
                cleaned['birth_date'] = cleaned.get('birth_date') or None
                cleaned['email'] = cleaned.get('email') or None
                values = ClientInput(**cleaned).model_dump()
            else:
                client = clients_by_external.get(record.get('client_external_id'))
                if not client:
                    raise HTTPException(409, 'Cliente de origem inexistente; valide novamente')
                values = {k: v for k, v in record.items() if k in TransactionInput.model_fields}
                values['client_id'] = client.id
                values = TransactionInput(**values).model_dump()
            prepared.append((row.id, values))
        except ValidationError as exc:
            raise HTTPException(409, f'Linha {row.row_number} falhou integridade operacional: {exc.errors()[0]["msg"]}')
    # SQLAlchemy bulk insert/RETURNING keeps identity mapping explicit and avoids per-row round trips.
    if prepared and batch.dataset == 'clients':
        created = list(db.scalars(insert(Client).returning(Client), [v for _, v in prepared]))
        db.execute(insert(DimClient), [{'client_id': c.id, 'name': c.name, 'location': c.address} for c in created])
    elif prepared:
        created = list(db.scalars(insert(Transaction).returning(Transaction), [v for _, v in prepared]))
        transactions = {t.external_id: t for t in created}
        completed = [(row_id, transactions[v['external_id']]) for row_id, v in prepared if v['status'] == 'COMPLETED']
        client_dimensions = {d.client_id: d.id for d in db.scalars(select(DimClient))}
        time_dimensions = {d.day_date: d.id for d in db.scalars(select(DimTime))}
        operation_dimensions = {d.code: d.id for d in db.scalars(select(DimOperation))}
        clients_by_id = {c.id: c for c in clients_by_external.values()}
        missing_clients = {t.client_id for _, t in completed} - set(client_dimensions)
        if missing_clients:
            dimensions = db.scalars(insert(DimClient).returning(DimClient), [
                {'client_id': id, 'name': clients_by_id[id].name, 'location': clients_by_id[id].address} for id in sorted(missing_clients)])
            client_dimensions.update({d.client_id: d.id for d in dimensions})
        missing_days = {t.occurred_at.date() for _, t in completed} - set(time_dimensions)
        if missing_days:
            dimensions = db.scalars(insert(DimTime).returning(DimTime), [
                {'day_date': d, 'day': d.day, 'month': d.month, 'year': d.year, 'quarter': (d.month-1)//3+1} for d in sorted(missing_days)])
            time_dimensions.update({d.day_date: d.id for d in dimensions})
        missing_operations = {t.operation for _, t in completed} - set(operation_dimensions)
        if missing_operations:
            dimensions = db.scalars(insert(DimOperation).returning(DimOperation), [
                {'code': op, 'description': op.title()} for op in sorted(missing_operations)])
            operation_dimensions.update({d.code: d.id for d in dimensions})
        facts = []
        for row_id, tx in completed:
            facts.append({'transaction_id': tx.id, 'client_sk': client_dimensions[tx.client_id],
                          'time_sk': time_dimensions[tx.occurred_at.date()], 'operation_sk': operation_dimensions[tx.operation],
                          'row_id': row_id, 'etl_id': run.id, 'amount': tx.amount, 'currency': tx.currency, 'quantity': 1})
            source_totals[tx.currency] = source_totals.get(tx.currency, Decimal(0)) + tx.amount
        if facts:
            db.execute(insert(Fact), facts)
    if prepared:
        db.execute(update(StageRow).where(StageRow.id.in_([id for id, _ in prepared])).values(loaded=True))
    run.loaded = len(prepared)
    db.flush()
    for fact in db.scalars(select(Fact).where(Fact.etl_id == run.id)):
        target_totals[fact.currency] = target_totals.get(fact.currency, Decimal(0)) + fact.amount
    run.reconciliation = [{'currency': c, 'source': str(v), 'warehouse': str(target_totals.get(c, Decimal(0))),
                            'difference': str(v - target_totals.get(c, Decimal(0))), 'justification': None}
                           for c, v in source_totals.items()]
    run.finished_at = now()
    if batch.dataset == 'transactions':
        # A batch is a report delivery unit; deadline is D+1 end of day in Maputo (UTC+2).
        timestamps = [parse_date(r.data['occurred_at']) for r in rows if r.id not in blocked and r.data.get('occurred_at')]
        if timestamps:
            local_day = max(timestamps).astimezone(timezone(timedelta(hours=2))).date()
            run.deadline = datetime.combine(local_day + timedelta(days=settings().report_deadline_days + 1), datetime.min.time(), tzinfo=timezone(timedelta(hours=2))).astimezone(timezone.utc)
            run.on_time = run.finished_at < run.deadline
    run.status = 'SUCCESS'
    batch.status = 'PROCESSED'
    etl_key, wh_key, report_key = f'etl:{run.id}', f'warehouse:{run.id}', f'report:{run.id}'
    node(db, batch, etl_key, f'ETL #{run.id}', 'ETL', 'Pandas: normalização; Decimal; dimensões; elegibilidade COMPLETED')
    node(db, batch, wh_key, f'Warehouse / lote {batch.id}', 'WAREHOUSE', f'{run.loaded} registos carregados')
    node(db, batch, report_key, f'Relatório #{run.id}', 'REPORT', 'Volume por dia, mês, operação e moeda; reconciliação')
    edge(db, f'validation:{validation.id}', etl_key, 'Apenas linhas conformes; invariantes operacionais obrigatórias')
    edge(db, etl_key, wh_key, 'Carga atómica; chaves únicas por transacção e linha de staging')
    edge(db, wh_key, report_key, 'Agregação por moeda, data e operação')
    dataset = db.scalar(select(Dataset).where(Dataset.name == batch.dataset))
    if dataset:
        dataset.updated_at = now()
    return run
