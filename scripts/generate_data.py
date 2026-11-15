"""Deterministic synthetic records, never real personal data."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate(output, clients=10000, transactions=30000):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    client_fields = ['external_id','name','document','phone','email','birth_date','address','source']
    tx_fields = ['external_id','client_external_id','operation','amount','currency','occurred_at','status','source','external_ref']
    with (output/'clients.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=client_fields)
        writer.writeheader()
        for i in range(1, clients+1):
            writer.writerow(dict(external_id=f'C{i:06}', name='' if i % 100 == 0 else f'Cliente Sintético {i}',
                                 document=f'DEMO-{i-1 if i % 125 == 0 else i:08}', phone='' if i % 80 == 0 else f'+25884{i:07}',
                                 email='invalido' if i % 200 == 0 else f'cliente{i}@example.invalid', birth_date='1990-01-15',
                                 address=['Maputo','Beira','Nampula','Tete'][i % 4], source='SYNTHETIC'))
    base = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)-timedelta(days=30)
    with (output/'transactions.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=tx_fields)
        writer.writeheader()
        for i in range(1, transactions+1):
            writer.writerow(dict(external_id=f'T{i:07}', client_external_id=f'C{(i-1)%clients+1:06}',
                                 operation=['DEPOSIT','WITHDRAWAL','TRANSFER','PAYMENT'][i % 4],
                                 amount='-25.00' if i % 150 == 0 else f'{100+i%20000}.{i%100:02}', currency='USD' if i%50 == 0 else 'MZN',
                                 occurred_at='2099-01-01T00:00:00Z' if i%333 == 0 else (base+timedelta(minutes=i)).isoformat(),
                                 status='PENDING' if i%100 == 0 else 'COMPLETED', source='SYNTHETIC', external_ref=f'REF-{i-1 if i%250 == 0 else i:08}'))
    print(f'Criados {clients} clientes e {transactions} transacções em {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='datasets')
    parser.add_argument('--clients', type=int, default=10000)
    parser.add_argument('--transactions', type=int, default=30000)
    args = parser.parse_args()
    if args.clients < 1 or args.transactions < 1:
        parser.error('As contagens devem ser positivas')
    generate(args.output, args.clients, args.transactions)
