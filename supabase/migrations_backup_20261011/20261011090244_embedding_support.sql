-- HydroVision: Embedding support
-- Target model: intfloat/multilingual-e5-small
-- Output dimensions: 384
-- Review locally before applying to Supabase.

-- Enable pgvector in the extensions schema.
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Store embeddings for document chunks.
ALTER TABLE public.knowledge_chunks
    ADD COLUMN embedding extensions.vector(384);

-- Store embeddings for historical event memory.
ALTER TABLE public.event_memory
    ADD COLUMN embedding extensions.vector(384);

-- Approximate nearest-neighbour indexes.
-- HNSW indexes are created after embeddings are populated,
-- to avoid indexing an empty table during initial setup.