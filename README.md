# MobiFin Data Management Platform

Plataforma académica de governação, qualidade e linhagem de dados financeiros. ISUTC · Engenharia de Dados · Docente: Simião Langa · Edmilson Conge, Ayrton Nhaguaga e Abelardo Pedro.

## Executar no Windows

Pré-requisitos: Docker Desktop activo, Docker Compose e PowerShell.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
docker compose up --build
```

O script preserva configurações existentes e gera três segredos aleatórios em `.env`, ignorado pelo Git. Alternativamente copie `.env.example` para `.env` e substitua todos os marcadores. A base de dados persiste num volume Docker; migrações e contas iniciais são criadas automaticamente.

- Frontend: http://localhost:8080
- API e Swagger: http://localhost:8000/docs
- Saúde: http://localhost:8000/api/health
- PostgreSQL: apenas rede interna do Compose, sem porta publicada.

Contas iniciais: `admin`, `owner`, `steward`, `engineer`, `auditor`. A palavra-passe inicial é o valor **local** de `DEMO_PASSWORD` em `.env`; não existe palavra-passe fixa neste repositório. Alterar pelo ícone de chave na barra superior. A mudança revoga todas as sessões dessa conta. Alterar `.env` depois da inicialização não redefine palavras-passe existentes.

## Demonstração

Os CSV em `datasets/` contêm 10 000 clientes e 30 000 transacções sintéticas, incluindo erros intencionais. Podem ser regenerados:

```powershell
python scripts/generate_data.py
```

1. Entrar como `admin` e importar `datasets/clients.csv`.
2. Em Data Quality seleccionar o lote e executar validação.
3. Consultar resultados, denominadores e incidentes; corrigir uma linha em Importação → Staging.
4. Revalidar e comparar as execuções. Tratar o incidente com atribuição, evidência e validação.
5. Em ETL processar clientes. Depois importar e processar transacções.
6. Consultar dashboard, relatórios por moeda e Data Lineage. Rastrear o ID interno de uma transacção consolidada.
7. Repetir o ETL do mesmo lote: é devolvida a execução existente, sem duplicar o warehouse.

Guia detalhado: [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## Desenvolvimento e testes

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm.cmd ci
npm.cmd test
npm.cmd run build
```

`backend/requirements.lock.txt` e `frontend/package-lock.json` registam as versões verificadas. O Docker usa esses ficheiros para instalações reproduzíveis. Para instalar exactamente o ambiente Python testado, usar `-r backend/requirements.lock.txt`.

Para desenvolvimento do frontend, `npm.cmd run dev` usa http://localhost:5173 e encaminha `/api` para http://localhost:8000. Para iniciar o backend fora do Docker, exporte `DATABASE_URL`, `JWT_SECRET` e `DEMO_PASSWORD`, execute `alembic upgrade head`, `python -m scripts.init_db` e `uvicorn app.main:app --reload` a partir de `backend/`.

Alternativa local verificada, mantendo PostgreSQL no Docker:

```powershell
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db
cd backend
..\.venv\Scripts\python.exe -m scripts.run_local
```

Noutro terminal, iniciar `npm.cmd run dev` em frontend. Para executar o cenário HTTP completo: `..\.venv\Scripts\python.exe -m scripts.demo` em backend. Este comando importa os datasets, valida, corrige um nome vazio, revalida, processa os dois lotes e verifica a idempotência. Para modo SQLite de desenvolvimento, acrescentar `--sqlite` ao launcher.

SQLite é suportado exclusivamente como alternativa de teste/local: `DATABASE_URL=sqlite:///./local.db`. Os testes traduzem os seis schemas para um namespace SQLite; essa verificação não substitui a execução em PostgreSQL. Os segredos são obrigatórios mesmo no modo local.

## Estrutura

```text
backend/
  app/core/          configuração, sessões SQLAlchemy, JWT, RBAC, auditoria
  app/models.py     modelos dos seis schemas
  app/schemas.py    contratos e validações Pydantic
  app/main.py       API REST, relatórios e dashboard
  app/quality.py    regras, indicadores e detecção de incidentes
  app/etl.py        pipeline Pandas, dimensões, factos e reconciliação
  app/lineage.py    persistência do grafo de linhagem
  app/seed.py       contas, regras, catálogo e política iniciais
  alembic/          migração inicial
  scripts/          inicialização
  tests/            testes de integração e segurança
frontend/src/       React, TypeScript, páginas, API, estilos e testes
database/          notas de administração PostgreSQL
datasets/          ficheiros sintéticos demonstrativos
scripts/           configuração segura e geração dos datasets
docs/              arquitectura, dados, API e guias
docker-compose.yml PostgreSQL + FastAPI + React/Nginx
```

A separação modular usa ficheiros por responsabilidade em vez de dezenas de pacotes vazios. Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, Pandas, PostgreSQL, PyJWT, Argon2, Pytest; React, Vite, TypeScript, Tailwind, React Router, Axios, TanStack Query, React Flow, Recharts, Lucide; Docker Compose.

## Estado e limites

Consulte [docs/VALIDATION.md](docs/VALIDATION.md) para os comandos executados e limites da verificação. A apresentação `MobiFin_Apresentacao_Academica_Melhorada(1).pptx` não estava presente na pasta recebida. Os requisitos foram extraídos do texto fornecido; a conformidade com os slides precisa de revisão quando forem disponibilizados. Resultados dos slides nunca são injectados nos indicadores.

Validação nesta sessão: 11 testes backend passaram em SQLite e em PostgreSQL; 5 testes frontend passaram; build de produção passou. A demonstração HTTP processou os CSV completos e persistiu 9 661 clientes, 28 815 transacções e 28 813 factos. A carga final de movimentos levou 18,609 segundos, com diferenças monetárias zero em MZN e USD. Evidência agregada em [docs/DEMO_RESULTS.json](docs/DEMO_RESULTS.json). A construção integral das imagens ficou por validar devido ao DNS do registry Docker; o modo local com PostgreSQL no Docker foi efectivamente executado.

ETL é síncrono e transaccional, apropriado ao cenário académico; não há filas ou serviços pagos. Transacções já consolidadas são imutáveis; use operações compensatórias. Dados manuais permanecem operacionais: o cenário de carga dimensional e linhagem por registo usa os lotes CSV. As páginas de staging e violações mostram 50 registos por consulta; paginação adicional está disponível pela API. Não existe eliminação física de registos financeiros.

Referências técnicas consultadas: [FastAPI: JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) e [SQLAlchemy: schemas e execution options](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html).
