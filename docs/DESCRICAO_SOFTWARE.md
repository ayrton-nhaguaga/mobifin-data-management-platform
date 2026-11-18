# Descrição e funcionamento do software MobiFin

## 1. Apresentação

O MobiFin é uma plataforma académica de gestão, governação, qualidade e linhagem de dados financeiros. A empresa e os dados fornecidos para demonstração são fictícios. O sistema permite importar dados de clientes e transacções, identificar e corrigir problemas, carregar os registos válidos e consultar indicadores, relatórios e evidências do processamento. Não é um sistema de pagamentos.

## 2. Componentes

- **Interface:** aplicação React acessível pelo navegador, onde o utilizador executa as operações e consulta os resultados.
- **API:** serviço FastAPI que aplica as regras de negócio, valida os pedidos e controla as permissões.
- **Base de dados:** PostgreSQL, com armazenamento persistente no Docker. SQLite existe como alternativa local e de teste.
- **Processamento ETL:** extrai os dados importados, valida e transforma os registos e carrega os dados elegíveis para as áreas operacional e analítica.
- **Auditoria e linhagem:** registam as acções relevantes e o percurso dos dados entre a importação e os resultados.

O fluxo principal é: **CSV → staging → validação → correcção → ETL → dados operacionais e analíticos → relatórios e linhagem**. Staging é a área temporária onde os dados importados podem conter erros sem afectar directamente os dados operacionais.

## 3. Como iniciar e aceder

1. Iniciar o Docker Desktop.
2. Na pasta principal do projecto, executar `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1` para preparar a configuração, se necessário. O script preserva as configurações existentes.
3. Executar `docker compose up --build` e aguardar que os serviços estejam disponíveis.
4. Abrir [http://localhost:8080](http://localhost:8080). A documentação interactiva da API fica em [http://localhost:8000/docs](http://localhost:8000/docs) e o estado da API em [http://localhost:8000/api/health](http://localhost:8000/api/health).
5. Entrar com uma das contas iniciais: `admin`, `owner`, `steward`, `engineer` ou `auditor`. A palavra-passe inicial é o valor local de `DEMO_PASSWORD` no ficheiro `.env`. Alterar esse valor depois da inicialização não altera automaticamente as palavras-passe já criadas.

A sessão usa um token mantido na memória da interface. Ao actualizar a página é necessário entrar novamente. O ícone de chave permite alterar a palavra-passe; a alteração revoga as sessões anteriores da conta.

## 4. Perfis de acesso

| Perfil | Conta inicial | Responsabilidade principal |
|---|---|---|
| Administrador | `admin` | Administração e acesso às funções da plataforma. |
| Proprietário dos dados | `owner` | Gestão de políticas, responsabilidades e classificações. |
| Responsável pela qualidade | `steward` | Gestão de regras, correcções e incidentes. |
| Engenheiro de dados | `engineer` | Importação e processamento ETL. |
| Auditor | `auditor` | Consulta de auditoria e dados autorizados. |

A API verifica as permissões em cada operação. Os perfis owner e auditor recebem dados de identificação pessoal mascarados na leitura operacional; os dados brutos de staging são reservados aos perfis técnicos autorizados.

## 5. Utilização passo a passo

### 5.1 Consultar e gerir dados operacionais

Nas páginas de clientes e transacções, o utilizador autorizado pode pesquisar, paginar, criar e editar registos. Nas transacções, o identificador do cliente é o ID interno da API, diferente do código externo do CSV. Transacções já consolidadas não podem ser reescritas; operações compensatórias devem ser usadas quando necessário.

### 5.2 Importar ficheiros

1. Abrir **Importação** e escolher o tipo de dados: clientes ou transacções.
2. Seleccionar um ficheiro CSV em UTF-8 com os cabeçalhos exactos. Os exemplos estão em `datasets/`.
3. Confirmar a importação e consultar o lote criado em staging.
4. A importação preserva os dados originais e não os carrega imediatamente para a área operacional. Importar novamente um ficheiro idêntico devolve o lote existente.

O conjunto de demonstração contém 10 000 clientes e 30 000 transacções sintéticas, incluindo erros intencionais. Para um ensaio menor, pode executar `python scripts/generate_data.py --output datasets/quick --clients 200 --transactions 600` e usar os ficheiros produzidos.

### 5.3 Executar a validação de qualidade

1. Abrir **Data Quality**, seleccionar o lote e executar a validação.
2. Consultar **Validações** para ver o número de linhas avaliadas e rejeitadas, as métricas e as violações.
3. Abrir **Resultados** para consultar uma execução. Usar **Comparar** para comparar duas execuções do mesmo lote, por exemplo antes e depois de uma correcção.
4. Cada execução guarda a revisão do lote e uma fotografia das regras activas. Uma linha pode gerar várias violações; o número de rejeitados conta linhas distintas.

### 5.4 Corrigir dados e tratar incidentes

1. Em **Importação → Staging**, encontrar a linha e escolher **Corrigir**.
2. Editar os campos no JSON e informar uma justificação, sem acrescentar campos desconhecidos. O original é preservado e a revisão do lote é incrementada. Linhas já carregadas não podem ser corrigidas em staging.
3. Consultar o incidente associado à regra e à linha, atribuí-lo a um responsável técnico e avançar para `IN_PROGRESS`.
4. Após a correcção, avançar para `PENDING_VALIDATION` e executar novamente a validação.
5. Resolver o incidente com evidência concreta e, por fim, encerrá-lo. O sistema impede a resolução se a regra ainda falhar ou se a validação estiver desactualizada.

A interface apresenta as primeiras 50 linhas de staging e violações por consulta; a API permite consultar outras páginas.

### 5.5 Processar os dados por ETL

1. Processar primeiro o lote de **clientes**, para que as referências das transacções possam ser verificadas.
2. Importar, validar e processar o lote de **transacções**.
3. Consultar os totais carregados e rejeitados. As linhas com violações bloqueantes ficam de fora da carga e disponíveis para correcção.
4. Os dados válidos são carregados de forma transaccional. As transacções com estado `COMPLETED` elegíveis alimentam os factos analíticos; `PENDING` e `CANCELLED` não entram nesses factos.
5. Consultar a reconciliação por moeda. A repetição do ETL para a mesma revisão devolve a execução existente e evita duplicações.
6. Se uma referência passar a existir ou as regras mudarem, usar **Reprocessar rejeitados** para criar uma revisão explícita, revalidar e tentar as linhas pendentes.

### 5.6 Consultar indicadores, relatórios e linhagem

- **Dashboard:** apresenta indicadores calculados a partir das validações e cargas efectivas.
- **Relatórios:** permitem consultar agregados diários, mensais e por operação, filtrados por moeda. Os valores de moedas diferentes não são somados como se fossem equivalentes.
- **Linhagem:** permite seleccionar um lote ou introduzir o ID interno de uma transacção consolidada para consultar o percurso entre origem, validação, carga, facto e relatório. Os nós mostram metadados e a vista permite zoom e reposicionamento.
- **Governação e catálogo:** apresentam conjuntos de dados, responsáveis, classificações e políticas. As alterações de políticas mantêm as versões anteriores.
- **Auditoria:** permite a admin e auditor consultar eventos e associá-los a entidades e execuções. Não existem funções de edição ou remoção de eventos pela API.

## 6. Validações dos dados

### 6.1 Campos e formatos

| Verificação | Comportamento |
|---|---|
| Campos obrigatórios | Nos clientes: `external_id`, `name`, `document`, `phone` e `source`. Nas transacções: todos os campos do modelo CSV. |
| Identificadores e duplicações | Verifica o ID externo e o documento de clientes; nas transacções, o ID externo e o par fonte/referência externa. Todos os participantes numa duplicação dentro do lote são assinalados. Também são consideradas duplicações com os dados operacionais. |
| Email | É opcional para clientes; quando preenchido deve ter formato válido. |
| Telefone | Deve respeitar o formato aceite pela regra: dígitos, espaços e sinal `+` opcional, com 7 a 40 caracteres. |
| Datas | Devem ter formato ISO e não podem estar no futuro. |
| Montante | Deve ser finito e positivo, com até 16 dígitos inteiros e duas casas decimais. |
| Moeda | Aceita `MZN`, `USD`, `ZAR` e `EUR`. |
| Operação | Aceita `DEPOSIT`, `WITHDRAWAL`, `TRANSFER` e `PAYMENT`. |
| Referência de cliente | O cliente referido por uma transacção deve existir na área operacional. |
| Contrato da linha | O modelo Pydantic verifica adicionalmente tipos, comprimentos e valores permitidos. |

As regras activas determinam as métricas e as violações. As regras bloqueantes impedem a carga das linhas que falham; as não bloqueantes podem produzir evidências sem excluir automaticamente a linha. As regras iniciais de demonstração são bloqueantes. Mesmo que uma regra seja desactivada, os contratos e as restrições da base de dados continuam a aplicar-se; uma falha de integridade pode reverter a carga inteira.

### 6.2 Indicadores e metas

| Dimensão | Como é calculada | Meta |
|---|---|---|
| Completude | Linhas sem falhas nas regras de campos obrigatórios ÷ total de linhas do lote. | ≥ 98% |
| Unicidade | Linhas sem falhas nas regras de unicidade ÷ total de linhas do lote. | ≥ 99% |
| Validade | Avaliações de regra/linha conformes ÷ total de avaliações de validade activas. | ≥ 99,5% |
| Actualidade | Entregas ETL de transacções concluídas antes do prazo ÷ entregas com prazo calculável. | ≥ 99% |
| Consistência | Diferenças financeiras não nulas justificadas ÷ diferenças não nulas apuradas por execução e moeda. | 100% |

Cada percentagem multiplica a razão por 100. Sem denominador, o indicador aparece como `—`/N/A. No dashboard, completude, unicidade e validade agregam os numeradores e denominadores da última validação de cada lote; não são médias simples de percentagens. Os resultados reflectem os dados efectivamente processados, e as metas são referências, não resultados garantidos.

A actualidade usa a maior data de operação processável do lote como referência, em Maputo. O prazo padrão é o início de D+2, exclusivo, correspondendo ao fim de D+1; pode ser configurado por `REPORT_DEADLINE_DAYS`. A medida representa entregas por lote, não um calendário completo de relatórios esperados. Dados históricos podem produzir entregas atrasadas.

A reconciliação compara os montantes das transacções `COMPLETED` novas e elegíveis com os factos da mesma execução, por moeda. Uma diferença zero é uma reconciliação bem sucedida; se não houver diferenças não nulas, o indicador de diferenças justificadas é N/A. Uma diferença não nula pode ser justificada por administrador ou proprietário, com motivo e auditoria; se o valor mudar, a justificação anterior deixa de valer.

## 7. Segurança e integridade

As palavras-passe são armazenadas como hashes Argon2. A autenticação utiliza JWT com expiração e controlo de versão por utilizador; logout, alteração de palavra-passe e alterações de permissões revogam tokens anteriores. Após dez falhas de autenticação por utilizador em cinco minutos, novas tentativas são temporariamente suspensas. A base operacional aplica restrições de integridade e as cargas usam transacções para evitar resultados parciais em caso de falha.

## 8. Limites e verificações anteriores

O projecto é uma demonstração académica local: o ETL é síncrono, os dados de exemplo são sintéticos e as transacções manuais não têm o mesmo percurso de linhagem por lote. SQLite é uma alternativa local/de teste e não substitui a verificação em PostgreSQL. Para produção seriam necessários, entre outros, gestão de segredos, TLS, observabilidade e recuperação apropriados.

Segundo [VALIDATION.md](VALIDATION.md), em 15/11/2026 passaram 11 testes de backend em SQLite e PostgreSQL, cinco testes de frontend e o build do frontend. Um ensaio HTTP em PostgreSQL processou os dados completos e reconciliou MZN e USD sem diferença. Esses resultados descrevem aquela sessão, não uma nova execução de testes. A construção integral das imagens e o ensaio visual tinham limitações registadas nesse documento.

Para mais detalhes, consultar [manual de utilização](USER_GUIDE.md), [qualidade dos dados](DATA_QUALITY.md), [arquitectura](ARCHITECTURE.md), [API](API.md) e [guião de demonstração](DEMO_GUIDE.md).
