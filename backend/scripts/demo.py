"""Reproducible real HTTP demonstration; requires a running API and local .env."""
import argparse
import json
from pathlib import Path
import httpx
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--datasets', default='../datasets')
    args = parser.parse_args()
    config = dotenv_values('../.env')
    password = config.get('DEMO_PASSWORD')
    if not password:
        raise SystemExit('Execute scripts/setup.ps1 e configure ../.env primeiro')
    with httpx.Client(base_url=args.url, timeout=900) as client:
        def request(method, path, **kwargs):
            response = client.request(method, f'/api{path}', **kwargs)
            response.raise_for_status()
            return response.json()

        login = request('POST', '/auth/token', data={'username':'admin','password':password})
        client.headers['Authorization'] = f'Bearer {login["access_token"]}'
        batches, runs = [], []
        for dataset in ('clients', 'transactions'):
            file_path = Path(args.datasets) / f'{dataset}.csv'
            with file_path.open('rb') as file:
                batch = request('POST', f'/imports/{dataset}', files={'file':(file_path.name,file,'text/csv')})
            batches.append(batch['id'])
            before = request('POST', '/validations', json={'batch_id':batch['id']})
            print(f'{dataset}: lote #{batch["id"]}; {before["evaluated"]} avaliados; {before["rejected"]} rejeitados')
            # Correct one missing client name, preserving all other intentional errors.
            if dataset == 'clients':
                offset, corrected = 0, False
                while offset < batch['row_count'] and not corrected:
                    rows = request('GET', f'/batches/{batch["id"]}/rows?offset={offset}&limit=200')['items']
                    for row in rows:
                        if not row['loaded'] and not row['data'].get('name') and row['data'].get('phone'):
                            request('PATCH', f'/staging/{row["id"]}', json={'data':{'name':'Cliente Sintético Corrigido'},'reason':'Correcção demonstrativa de campo obrigatório vazio'})
                            corrected = True
                            print(f'  Nome corrigido na linha staging #{row["id"]}; original preservado')
                            break
                    offset += 200
                after = request('POST', '/validations', json={'batch_id':batch['id']})
                print('  Completude antes/depois:', before['metrics']['completeness']['percentage'], after['metrics']['completeness']['percentage'])
            run = request('POST', '/etl', json={'batch_id':batch['id']})
            repeated = request('POST', '/etl', json={'batch_id':batch['id']})
            assert run['id'] == repeated['id'], 'ETL idempotente deve devolver a mesma execução'
            runs.append(run['id'])
            print(f'  ETL #{run["id"]}: {run["loaded"]} carregados; reconciliação {run["reconciliation"]}')
        dashboard = request('GET', '/dashboard')
        report = {'batches':batches, 'etl_runs':runs, 'clients':dashboard['clients'], 'transactions':dashboard['transactions'],
                  'facts':dashboard['facts'], 'metrics':dashboard['metrics']}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print('Consulte /api/lineage e /api/reports; trate os incidentes pela interface.')


if __name__ == '__main__':
    main()
