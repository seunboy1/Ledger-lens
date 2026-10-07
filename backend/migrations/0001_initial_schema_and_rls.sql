-- Ledger Lens — initial schema.
-- Run after SQLAlchemy's Base.metadata.create_all (or an Alembic migration
-- built from app/db/models.py); this file only ADDS the pgvector extension
-- and the row-level security policies that models.py cannot express.

CREATE EXTENSION IF NOT EXISTS vector;

-- Every tenant-scoped table gets RLS enabled and a policy that only
-- matches rows whose tenant_id equals the session's current tenant.
-- The application sets this once per request (see app/db/tenant.py) —
-- it is NOT trusted to filter correctly in application code; the database
-- refuses to return a mismatched row even if a query forgets a WHERE clause.

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_transactions ON transactions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_documents ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Messages are scoped indirectly via their conversation's tenant, since the
-- table itself has no tenant_id column — join-based policy.
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_messages ON messages
    USING (
        conversation_id IN (
            SELECT id FROM conversations
            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
        )
    );

-- layout_specs is intentionally NOT tenant-scoped: bank statement layouts
-- are a shared resource across tenants (that's the whole point of the
-- cache — one bank's layout, once learned, serves every tenant).

-- Index to support fast pgvector similarity search on the semantic path.
CREATE INDEX IF NOT EXISTS ix_transactions_embedding
    ON transactions USING hnsw (embedding vector_cosine_ops);
