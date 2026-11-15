# Manual de utilização

Inicie a plataforma conforme README. Use um dos utilizadores iniciais e a DEMO_PASSWORD guardada localmente em `.env`. A interface mantém token em memória, pelo que recarregar a página exige novo login. O ícone de chave altera a palavra-passe; a saída revoga todas as sessões da conta.

**Clientes e transacções:** pesquisar, paginar, criar e editar pelos formulários. IDs de cliente nas transacções são IDs internos da API, não códigos externos do CSV. Transacções consolidadas não admitem reescrita. Consulte as moedas separadamente.

**Importação:** seleccionar clientes ou transacções e CSV UTF-8 com cabeçalhos exactos. Usar os exemplos de datasets. Importar não carrega dados para o operacional; staging pode conter campos vazios, duplicados e formatos errados. Repetir o mesmo ficheiro devolve o lote existente.

**Data Quality:** seleccionar lote e executar. A página Validações mostra universo, rejeitados, métricas e violações. Resultados permite seleccionar uma execução; Comparar selecciona a segunda. Comparações relevantes usam mesmo lote e regras conhecidas. Sem dados avaliados, indicadores aparecem como `—`.

**Correcções:** Importação → Staging → Corrigir. Editar o JSON de campos e escrever justificação. Não alterar a estrutura para incluir campos desconhecidos. Linha carregada não pode ser corrigida em staging. O original permanece consultável pela API. Para procurar linhas além das primeiras 50 use GET /api/batches/{id}/rows?offset=50.

**Incidentes:** consultar a linha/regra afectadas e atribuir a `steward` (ou outro perfil técnico activo). Avançar para IN_PROGRESS, corrigir staging e passar para PENDING_VALIDATION. Reexecutar Data Quality. Resolver com evidência concreta e finalmente encerrar. O backend recusa resolver se a regra ainda falhar ou se a validação estiver desactualizada.

**ETL:** processar primeiro clientes, depois transacções. Confirmar carga. Dados válidos são carregados transaccionalmente, transacções COMPLETED alimentam os factos. Reconciliação compara montantes na mesma moeda. Repetição da mesma revisão não duplica. Rejeitados permanecem disponíveis para correcção. Se um cliente antes inexistente passar a existir, ou as regras mudarem sem correcção do CSV, usar Reprocessar rejeitados: cria uma revisão explícita, volta a validar e tenta apenas linhas pendentes. Cada nova tentativa fica auditada.

**Governance e catálogo:** owner/admin definem políticas, responsáveis e classificações. Cada edição de política preserva versão anterior. Campos pessoais permanecem restritos. Os restantes utilizadores consultam as responsabilidades e metadados.

**Linhagem:** seleccionar lote ou introduzir ID interno de transacção consolidada. Seleccionar nós revela metadados; os controlos permitem zoom e reposicionamento da vista. Transacções manuais sem carga ETL não têm facto rastreável.

**Relatórios e auditoria:** relatórios diários, mensais e por operação, filtrados por moeda. Auditoria acessível a admin/auditor; sem edição. IDs de entidades e execuções permitem relacionar evidências sem registar senhas ou tokens.
