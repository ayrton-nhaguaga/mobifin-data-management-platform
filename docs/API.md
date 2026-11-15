# API REST

Base: `/api`. Swagger: http://localhost:8000/docs; contrato completo: `/openapi.json`. Login usa formulário URL-encoded; restantes pedidos usam JSON, excepto upload multipart. O cabeçalho de acesso é `Authorization: Bearer <access_token>`.

```http
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=<DEMO_PASSWORD local>
```

| Rotas | Operações e permissões |
|---|---|
| GET /health | Saúde da API e ligação SQL; pública |
| POST /auth/token | Login, JWT com expiração; pública |
| GET /auth/me | Utilizador actual |
| POST /auth/logout, /auth/password | Revogação e alteração segura de senha |
| GET, POST /users; PATCH /users/{id} | Apenas ADMIN |
| GET /clients, /clients/{id} | Todos autenticados, campos pessoais mascarados para owner/auditor |
| POST /clients; PUT /clients/{id} | ADMIN, DATA_STEWARD, DATA_ENGINEER |
| GET /transactions, /transactions/{id} | Todos autenticados |
| POST /transactions; PUT /transactions/{id} | Perfis técnicos; actualização bloqueada após consolidação |
| POST /imports/{clients\|transactions} | ADMIN, DATA_ENGINEER; multipart file CSV |
| GET /batches | Todos autenticados |
| GET /batches/{id}/rows | Perfis técnicos, paginação offset/limit |
| PATCH /staging/{id} | ADMIN, DATA_STEWARD; data e reason obrigatórios |
| GET, POST /rules; PATCH /rules/{id} | Leitura todos; escrita ADMIN/DATA_STEWARD |
| GET, POST /validations | Leitura todos; execução perfis técnicos; body batch_id |
| GET /violations | Filtros run_id, dimension, offset |
| GET, POST /etl | Leitura todos; execução ADMIN/DATA_ENGINEER; body batch_id |
| POST /etl/retry | ADMIN/DATA_ENGINEER; nova revisão explícita para tentar linhas pendentes após alterações nas dependências/regras |
| POST /etl/{id}/reconcile | ADMIN/DATA_ENGINEER/AUDITOR; recompara snapshot de origem e factos actuais |
| POST /etl/{id}/justify | ADMIN/DATA_OWNER; currency e reason, apenas diferenças não nulas |
| GET /catalog; PUT /catalog/{id} | Leitura todos; escrita ADMIN/DATA_OWNER |
| GET, POST /policies; PUT /policies/{id} | Leitura todos; escrita ADMIN/DATA_OWNER com versões |
| GET /incidents; PATCH /incidents/{id} | Leitura todos; transições ADMIN/DATA_STEWARD |
| GET /audit | ADMIN/AUDITOR; filtros action, offset |
| GET /lineage | Filtros batch_id ou transaction_id |
| GET /dashboard, /reports | Todos autenticados; métricas reais e agregados por moeda |

Listagens devolvem `{items,total,offset,limit}` quando paginadas. Clientes: q/source, offset/limit até 200. Transacções: q/currency/operation/status, offset/limit até 200. Ordenação padrão por ID descendente. Lotes/regras/execuções devolvem até 200 entradas; regras e execuções mantêm histórico persistido.

Correcção de staging:

```json
{"data":{"name":"Cliente Sintético Corrigido"},"reason":"Nome preenchido após verificação da origem sintética"}
```

Transição de incidente:

```json
{"status":"ASSIGNED","assignee":"steward"}
```

Estados: OPEN → ASSIGNED → IN_PROGRESS → PENDING_VALIDATION → RESOLVED → CLOSED. PENDING_VALIDATION pode voltar a IN_PROGRESS. Resolver/encerrar exige evidência e última validação da revisão actual, com regra activa e sem violação dessa linha. Nova falha reabre incidente anteriormente encerrado/resolvido.

Erros: 401 credenciais/sessão; 403 perfil; 404 referência; 409 conflito ou transição inválida; 413 tamanho; 422 formato/contrato; 429 tentativas. Erros de integridade não expõem SQL. Não há endpoints para apagar auditoria ou dados financeiros. Dinheiro é string decimal nas respostas; percentagens são números calculados.
