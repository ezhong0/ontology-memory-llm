-- Database initialization script
-- This script runs automatically when PostgreSQL container starts
-- (via docker-compose.yml volume mount to /docker-entrypoint-initdb.d/)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- UUID generation
CREATE EXTENSION IF NOT EXISTS "vector";           -- Vector similarity search (pgvector)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram fuzzy matching (for entity resolution)

-- Create schemas
CREATE SCHEMA IF NOT EXISTS app;                   -- Application memory tables
CREATE SCHEMA IF NOT EXISTS domain;                -- Domain database mirror/cache (Phase 1C+)

-- Grant permissions to default user
GRANT ALL PRIVILEGES ON SCHEMA app TO memoryuser;
GRANT ALL PRIVILEGES ON SCHEMA domain TO memoryuser;

-- Set search path for convenience
ALTER DATABASE memorydb SET search_path TO app, domain, public;

-- Display installed extensions for verification
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('uuid-ossp', 'vector', 'pg_trgm');

-- Display created schemas
SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('app', 'domain');

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization complete!';
    RAISE NOTICE '  ✓ Extensions: uuid-ossp, vector (pgvector), pg_trgm';
    RAISE NOTICE '  ✓ Schemas: app, domain';
    RAISE NOTICE '  ✓ Ready for Alembic migrations';
END $$;
