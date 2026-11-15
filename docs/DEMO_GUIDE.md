# Guião académico · ISUTC

Disciplina: Engenharia de Dados. Docente: Simião Langa. Integrantes: Edmilson Conge, Ayrton Nhaguaga e Abelardo Pedro. Empresa fictícia: MobiFin, Lda.

## Preparação

Executar setup e `docker compose up --build`. Confirmar saúde API e entrar como admin. CSV completos em datasets têm 10 000 clientes/30 000 transacções. Para um ensaio rápido sem substituir esses ficheiros:

```powershell
python scripts/generate_data.py --output datasets/quick --clients 200 --transactions 600
```

Usar uma base nova ou ficheiros com IDs diferentes para repetir uma demonstração integral. Ficheiros idênticos não criam novos lotes. Não remover o volume para repetir sem decidir conscientemente perder os dados locais.

## Apresentação (12–15 minutos)

1. **Problema (1 min):** a plataforma gere confiança em dados financeiros; não é um sistema de pagamentos. Distinguir governação (responsabilidade/políticas), qualidade (regras e medidas) e linhagem (percurso e evidência).
2. **Governação (2 min):** mostrar três domínios, cinco papéis e quatro classificações. Versionar uma política. Mostrar a lista de regras com metas.
3. **Importação (2 min):** importar clientes. Mostrar que o operacional continua vazio. Ver staging e erros propositados, sem violar restrições de produção.
4. **Qualidade (2 min):** validar. Abrir resultados e explicar numerador, denominador e unidade. Duplicações contam todas as linhas envolvidas; validade usa avaliações de regra/linha. Os números vêm destes dados, não dos slides.
5. **Incidente (3 min):** encontrar a regra `name: required` de um cliente sem nome (gerador: múltiplos de 100). Atribuir a steward e avançar para IN_PROGRESS. Corrigir nome em staging com justificação. Passar para PENDING_VALIDATION, revalidar e resolver com evidência. Caso existam outros erros nessa linha, cada regra possui incidente separado. Tentar encerrar antes da validação demonstra o controlo. Comparar execuções antes/depois.
6. **ETL (2 min):** carregar clientes; importar e processar transacções. Mostrar carregados/rejeitados e reconciliação MZN/USD. Referências a clientes rejeitados são correctamente bloqueadas. Repetir ETL para demonstrar idempotência.
7. **Linhagem e análise (2 min):** abrir o grafo do lote de transacções; seleccionar uma transacção efectivamente carregada e rastrear o seu ID interno. Mostrar origem, validação, carga, facto e relatório. Consultar volume financeiro diário e mensal por moeda.
8. **Segurança e auditoria (1 min):** sair e entrar como auditor. Mostrar identificação mascarada, operações de leitura e eventos registados. A API aplica RBAC mesmo se um botão fosse manipulado.

## O que explicar sobre os indicadores

As metas são referência académica; não se prometem percentagens exactas dos slides. Correcções parciais aumentam indicadores proporcionalmente. Dados históricos podem falhar D+1. Sem diferenças monetárias, a proporção de diferenças justificadas é N/A; há reconciliações efectivas com diferença zero. O warehouse exclui PENDING/CANCELLED e rejeitados; isso não é perda injustificada de dados.

## Limitações a declarar

Slides não disponibilizados, portanto não foi possível confrontar a apresentação original. Modo académico local, ETL síncrono e prazo configurável (D+1 por omissão). Transacções manuais ficam fora da carga por lote nesta versão. Validar Docker/PostgreSQL na máquina da apresentação antes da aula, conforme docs/VALIDATION.md.
