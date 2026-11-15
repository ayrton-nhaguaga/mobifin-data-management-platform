# PostgreSQL

O Compose cria a base `mobifin`. Alembic cria operational, staging, warehouse, governance, quality e audit antes da migração inicial. Dados persistem no volume `postgres_data`.

Não há porta PostgreSQL exposta ao host. Administração local através de `docker compose exec db psql -U mobifin -d mobifin`. Backup: `docker compose exec -T db pg_dump -U mobifin mobifin > backup.sql` (verificar encoding do redireccionamento no PowerShell antes de restaurar). Credenciais aleatórias ficam em .env.

A conta de demonstração SQL é também a conta de migração. Protecção da auditoria é aplicada na API (sem endpoints de escrita directa), não contra um administrador SQL. Separar migrador e conta runtime com privilégios restritos seria uma evolução para produção.
