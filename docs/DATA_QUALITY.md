# Qualidade: universos, fórmulas e metas

Todos os resultados provêm de linhas efectivamente importadas ou cargas executadas. Percentagem sem denominador é `null`, apresentada como `—`. Não se usam os 91/98,5, 94/99,2 ou 96/99,6 dos slides como medições.

| Dimensão | Numerador | Denominador | Meta |
|---|---|---|---|
| Completude | Linhas sem falhas nas regras required activas | Todas as linhas do lote/revisão | ≥98% |
| Unicidade | Linhas sem falhas nas regras unique activas | Todas as linhas do lote/revisão | ≥99% |
| Validade | Pares regra/linha conformes | Todas as avaliações de regras de validade activas, incluindo schema | ≥99,5% |
| Actualidade | Entregas ETL de transacções concluídas antes do prazo | Execuções com data de referência e prazo calculável | ≥99% |
| Consistência | Diferenças financeiras não nulas com justificação | Diferenças não nulas apuradas, por execução e moeda | 100% |

Percentagem = numerador / denominador × 100. No dashboard as três primeiras dimensões somam numeradores e denominadores da **última validação de cada lote**. Não se faz média simples das percentagens. Lotes de clientes e transacções formam o universo de staging; não representam qualidade de todos os dados operacionais históricos. Cada execução mantém lote, revisão, instante e snapshot das regras.

Completude: obrigatórios para clientes: external_id, name, document, phone, source. Para transacções: todos os campos do modelo CSV. Duplicações de documento/ID ou (fonte, referência externa) rejeitam **todos os participantes** da duplicação no lote; não se escolhe arbitrariamente o primeiro. Também se consulta o operacional, excepto para a própria linha já carregada. Uma chave vazia conta na completude; não é contada como duplicação.

Validade: email opcional vazio é conforme; nome obrigatório vazio falha completude e também pode falhar o contrato estrutural, sendo esses denominadores explicitamente distintos. Valores monetários finitos, positivos, até 16 dígitos inteiros e duas casas; moedas MZN/USD/ZAR/EUR; operações DEPOSIT/WITHDRAWAL/TRANSFER/PAYMENT; datas ISO não futuras; cliente deve existir no operacional. `schema` aplica o contrato Pydantic de toda a linha como uma verificação adicional (comprimentos, enumerações e tipos). Não há eval ou código arbitrário em regras.

Actualidade: cada ETL de transacções com linhas válidas é uma entrega demonstrativa. D = maior data de operação processável nesse lote, em Maputo; prazo padrão = início de D+2, exclusivo (fim de D+1). `finished_at < deadline`. `REPORT_DEADLINE_DAYS` configura os dias até ao prazo (padrão 1; aceita 0–30). Os CSV históricos tendem a gerar entregas atrasadas; isso é um resultado real. Lotes vazios/rejeitados e cargas de clientes ficam excluídos. Esta aproximação mede entregas por lote, não um calendário completo de relatórios diários esperados.

Consistência: compara transacções COMPLETED novas e elegíveis da carga actual com factos dessa execução, agrupados por moeda. Rejeitados, PENDING/CANCELLED e linhas já carregadas ficam excluídos dos dois lados. Importações apenas de clientes não geram reconciliação monetária. Diferença = origem − warehouse; zeros são reconciliações bem sucedidas, não diferenças a justificar. Sem diferenças, o KPI de justificação é N/A e o dashboard informa o número de reconciliações e diferenças sem justificação. `POST /etl/{id}/reconcile` verifica novamente o snapshot de origem da carga contra os factos actuais. Uma diferença não nula pode ser justificada por ADMIN/DATA_OWNER com motivo, autor e instante; a auditoria preserva a evidência. Se a diferença mudar, a justificação anterior deixa de valer. Não há edição manual de montantes no warehouse pela API.

Rejeição é contagem de **linhas distintas**, não de violações. Uma linha pode gerar várias violações e incidentes. A carga exclui linhas com violações bloqueantes, identificadas pelo snapshot dessa validação; regras não bloqueantes produzem evidências e incidentes sem excluir automaticamente a linha. Regras de demonstração são todas bloqueantes. Regras desactivadas deixam de contribuir para as métricas; nunca removem restrições de integridade operacional. Se uma regra de integridade necessária for desactivada, o contrato Pydantic e as constraints SQL podem recusar a carga inteira com rollback.

Correcções: originais preservados; revisão incrementada; revalidação cria novo histórico. Comparar execuções do mesmo lote permite observar antes/depois sem confundir revisões com novos dados. Regras não devem ser desactivadas para simular correcções. Reprocessamento explícito dos rejeitados cria nova revisão e permite aplicar alterações nos clientes referenciados ou nas regras sem duplicar linhas já carregadas.
