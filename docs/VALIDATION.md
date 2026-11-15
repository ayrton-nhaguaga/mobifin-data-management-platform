# Validação executada

Ambiente: Windows, Python 3.12.5, Node 22.14.0, Docker Desktop 29.0.1, PostgreSQL 16 (container). Data da sessão: 15/11/2026, Africa/Maputo.

| Verificação | Resultado |
|---|---|
| Backend, Pytest e SQLite em memória com foreign keys | 11 testes passaram |
| Mesma bateria com PostgreSQL real, base isolada mobifin_test | 11 testes passaram |
| Frontend, Vitest/Testing Library | 5 testes passaram |
| TypeScript + Vite, build de produção | Passou |
| Alembic 0001 em PostgreSQL, base principal | Aplicada; 19 tabelas em seis schemas |
| Health via frontend/Vite → API → PostgreSQL | HTTP 200, status ok |
| OpenAPI/Swagger | HTTP 200 |
| Geração de dados | 10 000 clientes e 30 000 transacções sintéticas |
| Demonstração HTTP completa com PostgreSQL e ETL final em lote | 9 661 clientes, 28 815 transacções, 28 813 factos |
| Reconciliação de montantes na demonstração | MZN e USD com diferenças 0,00 |
| Correcção e revalidação de nome obrigatório | Completude de clientes: 98,00% → 98,01% |
| Construção integral dos containers | Bloqueada pelo DNS do registry na imagem python:3.12-slim |
| Verificação visual no navegador | Bloqueada: browser access host indisponível; captura de janela expirou |

Testes backend cobrem login/logout/expiração por revogação, alteração de palavra-passe, RBAC, CRUD operacional permitido, mascaramento, CSV inválido e idempotente, staging isolado, duplicações, regras e denominadores, KPIs sem dados, histórico, ETL, elegibilidade, moedas e Decimal, reconciliação exacta, idempotência, linhagem, incidentes, correcção com original preservado, validação antes de resolver/encerrar, políticas versionadas, permissões de utilizadores, detecção de uma falha externa no warehouse, justificação exclusiva por owner/admin e nova tentativa após corrigir uma referência.

Testes frontend cobrem redireccionamento de rota protegida, formulário de login, erro da API, carregamento, tratamento de erros, dashboard com resultados devolvidos pela API, navegação para clientes e logout. São testes de componentes com API simulada apenas nos testes; a aplicação usa endpoints reais. Não substituem um ensaio visual completo.

## Ensaio com o volume completo

`scripts.demo` foi executado por HTTP na API real, com os 40 000 registos CSV em PostgreSQL. A primeira carga por linha mostrou latência excessiva e foi interrompida; a transacção de movimentos foi revertida integralmente. A implementação foi substituída por inserções em lote com SQLAlchemy RETURNING e o cenário foi repetido com sucesso. Os testes em SQLite e PostgreSQL voltaram a passar após esta alteração.

Resultado final: 9 661 clientes operacionais; 28 815 transacções operacionais; 28 813 factos COMPLETED. Duas transacções PENDING ficam fora do warehouse por elegibilidade. O lote de movimentos rejeitou 1 185 linhas com violações reais. Reexecutar a mesma revisão devolveu a mesma execução, sem duplicar factos. Os originais e os erros remanescentes continuam em staging.

A carga final de 28 815 movimentos levou 18,609 segundos, incluindo validação, carga, dimensões, factos e reconciliação. Uma correcção incremental de cliente levou 0,349 segundos. Estes tempos são observações desta máquina e não constituem um benchmark geral. O teste final fez login através do proxy em localhost:5173, consultou indicadores e relatórios, rastreou uma transacção ao respectivo facto e confirmou 19 eventos de auditoria persistidos.

Reconciliação da carga de movimentos: MZN 241 625 491,94 na origem elegível e no warehouse; USD 1 336 080,00 nos dois lados. Diferenças zero, sem conversão entre moedas. Actualidade observada de 0% é esperada neste cenário histórico carregado depois de D+1; não foi substituída por um valor ilustrativo. Resultados agregados e evidência de linhagem: `DEMO_RESULTS.json`.

Advertências observadas: Starlette comunica futura substituição de httpx no seu TestClient; os testes actuais passam. Na primeira execução PostgreSQL o cache do Pytest encontrou uma restrição de permissões; o cache opcional foi desactivado em pytest.ini. Recharts 2 informa fim de manutenção do ramo; a versão instalada foi compilada e testada, ficando a actualização para v3 como manutenção futura.

## Repetir PostgreSQL

```powershell
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db
docker compose exec -T db psql -U mobifin -d postgres -c "CREATE DATABASE mobifin_test"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_postgres.ps1
```

Criar a base apenas na primeira vez. O fixture exige nome terminado em `_test` e recria as tabelas exclusivamente nessa base. Não executar duas baterias PostgreSQL em simultâneo na mesma base. Nenhum teste usa a base principal `mobifin`.

## Limites restantes

A rede do Docker não conseguiu resolver production.cloudfront.docker.com ao obter a imagem oficial Python. Por isso não se afirma que `docker compose up --build` tenha sido verificado integralmente. O Compose foi validado e PostgreSQL arrancou; API e frontend foram executados no host, ligados a esse PostgreSQL. Para reproduzir esse modo usar scripts.run_local e npm run dev, conforme README.

A apresentação PowerPoint referida não foi fornecida; a correspondência exacta com os slides continua por verificar. O ensaio visual e a construção das imagens devem ser repetidos num ambiente com browser e registry disponíveis.
