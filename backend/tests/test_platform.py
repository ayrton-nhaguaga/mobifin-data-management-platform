import csv
import io
from conftest import headers

CLIENT_FIELDS = ['external_id','name','document','phone','email','birth_date','address','source']
TX_FIELDS = ['external_id','client_external_id','operation','amount','currency','occurred_at','status','source','external_ref']


def cdata(**kwargs):
    return dict(dict(external_id='C1',name='Cliente Sintético',document='DEMO-001',phone='+258840000001',email='demo@example.invalid',birth_date='1990-01-01',address='Maputo',source='TEST'), **kwargs)


def tdata(**kwargs):
    return dict(dict(external_id='T1',client_external_id='C1',operation='DEPOSIT',amount='100.10',currency='MZN',occurred_at='2026-01-01T10:00:00Z',status='COMPLETED',source='TEST',external_ref='REF1'),**kwargs)


def upload(client, auth, dataset, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer,fieldnames=CLIENT_FIELDS if dataset=='clients' else TX_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    response = client.post(f'/api/imports/{dataset}',headers=auth,files={'file':('demo.csv',buffer.getvalue().encode(),'text/csv')})
    assert response.status_code == 201, response.text
    return response.json()


def etl(client, auth, batch):
    response = client.post('/api/etl',headers=auth,json={'batch_id':batch['id']})
    assert response.status_code == 200,response.text
    return response.json()


def test_auth_rbac_logout_and_password(client):
    assert client.get('/api/clients').status_code == 401
    assert client.post('/api/auth/token', data={'username':'admin','password':'wrong'}).status_code == 401
    auth = headers(client, 'auditor')
    assert client.post('/api/clients',headers=auth,json=cdata()).status_code == 403
    assert client.get('/api/batches/1/rows',headers=auth).status_code == 403
    assert client.get('/api/users',headers=auth).status_code == 403
    assert client.post('/api/auth/logout',headers=auth).status_code == 200
    assert client.get('/api/auth/me',headers=auth).status_code == 401
    auth=headers(client)
    assert client.post('/api/auth/password',headers=auth,json={'current_password':'wrong','new_password':'new-password-12345'}).status_code == 400
    assert client.post('/api/auth/password',headers=auth,json={'current_password':'Test-only-password-123!','new_password':'new-password-12345'}).status_code == 200
    assert client.get('/api/auth/me',headers=auth).status_code == 401
    audit=headers(client,'auditor')
    events=client.get('/api/audit',headers=audit).json()['items']
    assert any(e['action']=='LOGIN' and e['result']=='FAILURE' for e in events)
    assert 'password' not in str(events).lower().replace('password_change','')


def test_operational_crud_decimal_and_masking(client):
    auth=headers(client)
    created=client.post('/api/clients',headers=auth,json=cdata())
    assert created.status_code==201
    cid=created.json()['id']
    assert client.put(f'/api/clients/{cid}',headers=auth,json=cdata(name='Cliente Actualizado')).status_code==200
    assert client.get('/api/clients?q=Actualizado',headers=auth).json()['total']==1
    assert client.post('/api/clients',headers=auth,json=cdata()).status_code==409
    assert client.get(f'/api/clients/{cid}',headers=headers(client,'auditor')).json()['document']=='••••'
    tx=tdata();tx.pop('client_external_id');tx['client_id']=cid
    res=client.post('/api/transactions',headers=auth,json=tx)
    assert res.status_code==201,res.text
    assert res.json()['amount']=='100.10'
    tx['amount']='250.20'
    assert client.put(f'/api/transactions/{res.json()["id"]}',headers=auth,json=tx).status_code==200
    tx['amount']='NaN'
    assert client.post('/api/transactions',headers=auth,json=tx).status_code==422
    tx['amount']='-10'
    assert client.post('/api/transactions',headers=auth,json=tx).status_code==422


def test_csv_structure_and_idempotent_import(client):
    auth=headers(client)
    assert client.post('/api/imports/clients',headers=auth,files={'file':('bad.csv',b'name\nX\n','text/csv')}).status_code==422
    assert client.post('/api/imports/clients',headers=auth,files={'file':('bad.txt',b'','text/plain')}).status_code==422
    assert client.post('/api/imports/clients',headers=auth,files={'file':('bad.csv',b'\xff','text/csv')}).status_code==422
    first=upload(client,auth,'clients',[cdata(name='')])
    second=upload(client,auth,'clients',[cdata(name='')])
    assert first['id']==second['id']
    assert client.get('/api/clients',headers=auth).json()['total']==0
    assert client.get('/api/batches/1/rows',headers=auth).json()['total']==1


def test_quality_denominators_duplicates_and_history(client):
    auth=headers(client)
    batch=upload(client,auth,'clients',[cdata(),cdata(external_id='C2'),cdata(external_id='C3',document='DEMO3',name='',email='invalid')])
    run=client.post('/api/validations',headers=auth,json={'batch_id':batch['id']}).json()
    assert run['evaluated']==3 and run['rejected']==3
    assert run['metrics']['completeness']['passed']==2
    assert run['metrics']['uniqueness']['passed']==1
    assert run['metrics']['validity']['denominator']==12
    assert run['metrics']['validity']['passed']==10
    assert client.get('/api/incidents',headers=auth).json()['total']>=4
    dashboard=client.get('/api/dashboard',headers=auth).json()
    assert dashboard['metrics']['completeness']['denominator']==3
    client.post('/api/validations',headers=auth,json={'batch_id':batch['id']})
    assert client.get('/api/dashboard',headers=auth).json()['metrics']['completeness']['denominator']==3


def test_end_to_end_warehouse_reconciliation_lineage_idempotence(client):
    auth=headers(client)
    etl(client,auth,upload(client,auth,'clients',[cdata()]))
    batch=upload(client,auth,'transactions',[tdata(),tdata(external_id='T2',external_ref='REF2',amount='0.20'),tdata(external_id='T3',external_ref='REF3',currency='USD',amount='33.50'),tdata(external_id='T4',external_ref='REF4',amount='-10'),tdata(external_id='T5',external_ref='REF5',status='PENDING')])
    run=etl(client,auth,batch)
    assert run['loaded']==4 and run['rejected']==1
    assert etl(client,auth,batch)['id']==run['id']
    report=client.get('/api/reports',headers=auth).json()
    mzn=next(r for r in report['daily'] if r['currency']=='MZN')
    assert mzn['volume']=='100.30' and mzn['quantity']==2
    assert all(e['difference']=='0.00' for e in run['reconciliation'])
    assert client.get('/api/dashboard',headers=auth).json()['facts']==3
    trace=client.get('/api/lineage?transaction_id=1',headers=auth).json()
    assert len(trace['nodes'])==6 and len(trace['edges'])==5
    assert trace['trace']['etl_id']==run['id'] and trace['trace']['source_identifier']=='T1'
    audits=client.get('/api/audit?action=EXECUTE_ETL',headers=auth).json()
    assert audits['total']==3


def test_incident_correction_revalidation_and_verified_closure(client):
    auth=headers(client)
    batch=upload(client,auth,'clients',[cdata(name='')])
    client.post('/api/validations',headers=auth,json={'batch_id':batch['id']})
    incident=next(r for r in client.get('/api/incidents',headers=auth).json()['items'] if r['title']=='name: required')
    path=f'/api/incidents/{incident["id"]}'
    assert client.patch(path,headers=auth,json={'status':'CLOSED'}).status_code==409
    for status in ['ASSIGNED','IN_PROGRESS','PENDING_VALIDATION']:
        assert client.patch(path,headers=auth,json={'status':status,'assignee':'steward'}).status_code==200
    assert client.patch(path,headers=auth,json={'status':'RESOLVED','evidence':'Corrigido'}).status_code==409
    row=client.get(f'/api/batches/{batch["id"]}/rows',headers=auth).json()['items'][0]
    assert client.patch(f'/api/staging/{row["id"]}',headers=auth,json={'data':{'name':'Cliente Corrigido'},'reason':'Correcção demonstrativa do nome obrigatório'}).status_code==200
    assert client.patch(path,headers=auth,json={'status':'RESOLVED','evidence':'Nome corrigido'}).status_code==409
    after=client.post('/api/validations',headers=auth,json={'batch_id':batch['id']}).json()
    assert after['metrics']['completeness']['percentage']==100
    assert client.patch(path,headers=auth,json={'status':'RESOLVED','evidence':'Nome preenchido e regra reexecutada'}).status_code==200
    assert client.patch(path,headers=auth,json={'status':'CLOSED'}).status_code==200
    assert client.get(f'/api/batches/{batch["id"]}/rows',headers=auth).json()['items'][0]['original']['name']==''
    result=etl(client,auth,batch)
    assert result['loaded']==1
    assert client.patch(f'/api/staging/{row["id"]}',headers=auth,json={'data':{'name':'Outro'},'reason':'Não deve modificar dados carregados'}).status_code==409


def test_invalid_references_dates_and_schema_are_rejected(client):
    auth=headers(client)
    etl(client,auth,upload(client,auth,'clients',[cdata()]))
    batch=upload(client,auth,'transactions',[tdata(client_external_id='UNKNOWN'),tdata(external_id='T2',external_ref='REF2',occurred_at='2099-01-01'),tdata(external_id='T3',external_ref='REF3',status='UNKNOWN')])
    run=etl(client,auth,batch)
    assert run['loaded']==0 and run['rejected']==3
    assert client.get('/api/dashboard',headers=auth).json()['metrics']['timeliness']['percentage'] is None


def test_governance_versions_roles_and_user_revocation(client):
    auth=headers(client)
    owner=headers(client,'owner')
    data={'name':'Política de demonstração','content':'Dados restritos exigem autorização.','owner':'owner'}
    response=client.post('/api/policies',headers=owner,json=data)
    assert response.status_code==201
    data['content']='Dados restritos exigem autorização e auditoria.'
    updated=client.put(f'/api/policies/{response.json()["id"]}',headers=owner,json=data).json()
    assert updated['version']==2 and len(updated['history'])==1
    assert client.post('/api/rules',headers=owner,json={}).status_code==403
    auditor=headers(client,'auditor')
    uid=client.get('/api/auth/me',headers=auditor).json()['id']
    assert client.patch(f'/api/users/{uid}',headers=auth,json={'role':'AUDITOR','active':False}).status_code==200
    assert client.get('/api/auth/me',headers=auditor).status_code==401
    catalog=client.get('/api/catalog',headers=auth).json()
    assert len(catalog['items'])==3 and catalog['items'][0]['rules']


def test_empty_dashboard_has_no_invented_percentages(client):
    auth=headers(client)
    data=client.get('/api/dashboard',headers=auth).json()
    assert all(m['percentage'] is None for m in data['metrics'].values())
    assert data['clients']==0 and data['last_etl'] is None


def test_reconciliation_detects_and_requires_owner_justification(client):
    from app.core.db import get_db
    from app.main import app
    from app.models import Fact
    from decimal import Decimal
    from sqlalchemy import select
    auth=headers(client)
    etl(client,auth,upload(client,auth,'clients',[cdata()]))
    run=etl(client,auth,upload(client,auth,'transactions',[tdata()]))
    session_generator=app.dependency_overrides[get_db]()
    db=next(session_generator)
    # Simulate an external warehouse fault to exercise reconciliation independently of ETL.
    fact=db.scalar(select(Fact))
    fact.amount=Decimal('99.10')
    db.commit()
    session_generator.close()
    response=client.post(f'/api/etl/{run["id"]}/reconcile',headers=headers(client,'auditor'))
    assert response.status_code==200
    assert response.json()['reconciliation'][0]['difference']=='1.00'
    metrics=client.get('/api/dashboard',headers=auth).json()['metrics']['consistency']
    assert metrics['denominator']==1 and metrics['percentage']==0
    justification={'currency':'MZN','reason':'Diferença identificada no teste de recuperação; correcção aprovada pelo owner.'}
    assert client.post(f'/api/etl/{run["id"]}/justify',headers=headers(client,'engineer'),json=justification).status_code==403
    assert client.post(f'/api/etl/{run["id"]}/justify',headers=headers(client,'owner'),json=justification).status_code==200
    assert client.get('/api/dashboard',headers=auth).json()['metrics']['consistency']['percentage']==100


def test_retry_pending_rows_after_reference_is_fixed(client):
    auth=headers(client)
    batch=upload(client,auth,'transactions',[tdata()])
    first=etl(client,auth,batch)
    assert first['loaded']==0
    etl(client,auth,upload(client,auth,'clients',[cdata()]))
    assert etl(client,auth,batch)['id']==first['id']
    response=client.post('/api/etl/retry',headers=auth,json={'batch_id':batch['id']})
    assert response.status_code==200,response.text
    assert response.json()['loaded']==1 and response.json()['revision']==1
    assert client.get('/api/dashboard',headers=auth).json()['facts']==1
    assert client.post('/api/etl/retry',headers=auth,json={'batch_id':batch['id']}).status_code==409
