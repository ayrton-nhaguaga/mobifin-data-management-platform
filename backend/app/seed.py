from sqlalchemy import select
from app.core.security import hasher, ROLES
from app.core.config import settings
from app.models import User, Dataset, Rule, Policy
from app.quality import FIELDS, REQUIRED, TARGETS


def seed(db):
    if not db.scalar(select(User.id).limit(1)):
        for username, role in zip(('admin', 'owner', 'steward', 'engineer', 'auditor'), ROLES):
            db.add(User(username=username, full_name=role.replace('_', ' ').title(), role=role,
                        password_hash=hasher.hash(settings().demo_password)))
    if not db.scalar(select(Dataset.id).limit(1)):
        for name, description in [('clients', 'Cadastro sintético de clientes'), ('transactions', 'Transacções financeiras sintéticas'), ('reports', 'Agregados financeiros por moeda')]:
            types = {'amount':'decimal(18,2)', 'birth_date':'date', 'occurred_at':'timestamp UTC', 'quantity':'integer', 'volume':'decimal(18,2)', 'day':'date'}
            fields = [{'name': f, 'type': types.get(f, 'string'),
                       'classification': 'RESTRITA' if f in ('document', 'phone', 'email', 'birth_date') else 'CONFIDENCIAL'} for f in FIELDS.get(name, ['day', 'currency', 'volume', 'quantity'])]
            db.add(Dataset(name=name, description=description, source='CSV / API / ETL', owner='owner', steward='steward', classification='CONFIDENCIAL', fields=fields))
    if not db.scalar(select(Rule.id).limit(1)):
        for dataset in FIELDS:
            rules = [('required', field) for field in REQUIRED[dataset]]
            rules += [('unique', f) for f in (['external_id', 'document'] if dataset == 'clients' else ['external_id', 'external_ref'])]
            rules += [('email', 'email'), ('phone', 'phone'), ('date', 'birth_date')] if dataset == 'clients' else [('positive', 'amount'), ('date', 'occurred_at'), ('operation', 'operation'), ('currency', 'currency'), ('reference', 'client_external_id')]
            rules += [('schema', 'external_id')]
            for kind, field in rules:
                dimension = {'required': 'completeness', 'unique': 'uniqueness'}.get(kind, 'validity')
                db.add(Rule(dataset=dataset, name=f'{field}: {kind}', kind=kind, field=field, dimension=dimension, target=TARGETS[dimension]))
    if not db.scalar(select(Policy.id).limit(1)):
        db.add(Policy(name='Protecção e acesso a dados financeiros', content='Dados exclusivamente sintéticos. Acesso por papel; identificação pessoal mascarada para auditor e owner. Correcções e cargas deixam evidência de auditoria.', owner='owner'))
    db.commit()
