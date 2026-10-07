-- Statement-level balances for the document proof, and repair provenance
-- for rows changed after extraction (AI targeted repair or human review).
ALTER TABLE documents ADD COLUMN IF NOT EXISTS opening_balance NUMERIC(18, 2);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS closing_balance NUMERIC(18, 2);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS repair_source VARCHAR(16);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS page_number INTEGER;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS row_index INTEGER;
