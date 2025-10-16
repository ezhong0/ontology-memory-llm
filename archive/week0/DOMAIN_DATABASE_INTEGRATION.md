# Domain Database Integration Guide

**Date**: 2025-10-15
**Status**: Week 0 - Setup Instructions
**Phase**: Will be implemented in Phase 1C (Week 5-6)

---

## Overview

The memory system integrates with an **external domain database** (e.g., ERP system) to ground memories in actual business entities. This document outlines the integration approach for Week 0 setup.

---

## Week 0: Prerequisites

### 1. Database Configuration

The domain database connection is configured in `.env`:

```env
# Domain Database Configuration (external ERP system)
DOMAIN_DB_URL=postgresql://domainuser:domainpass@localhost:5432/domaindb
DOMAIN_DB_ENABLED=false  # Set to true when domain DB available
```

**Action Required**: Update `DOMAIN_DB_URL` with your actual domain database credentials.

### 2. Domain Schema Documentation

**Required**: Document your domain database schema before Phase 1C:

```
docs/domain/
├── SCHEMA.md              # Tables, columns, types, constraints
├── RELATIONSHIPS.md       # Foreign keys, entity relationships
└── SAMPLE_QUERIES.md      # Example queries for each entity type
```

**Key entity types** (customize for your domain):
- **Customers**: Companies/individuals (e.g., `customers` table)
- **Orders**: Purchase orders (e.g., `orders` table)
- **Invoices**: Billing documents (e.g., `invoices` table)
- **Products**: Items/services (e.g., `products` table)
- **Contacts**: People (e.g., `contacts` table)

### 3. Ontology Mapping

Create a mapping from conversational mentions to domain entities:

**Example `docs/domain/ONTOLOGY_MAPPING.md`**:

```markdown
| Entity Type | Domain Table | Key Column | Display Name Column | Search Columns |
|-------------|--------------|------------|---------------------|----------------|
| customer    | customers    | id         | name                | name, email, phone |
| order       | orders       | order_id   | order_number        | order_number, customer_id |
| invoice     | invoices     | invoice_id | invoice_number      | invoice_number, order_id |
| product     | products     | sku        | product_name        | sku, product_name, description |
```

This will be loaded into the `domain_ontology` table in Phase 1C.

### 4. Read-Only Access

**Best Practice**: Use a **read-only** database user for the memory system:

```sql
-- Create read-only user (run in your domain database)
CREATE USER memoryservice_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE domaindb TO memoryservice_readonly;
GRANT USAGE ON SCHEMA public TO memoryservice_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO memoryservice_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO memoryservice_readonly;
```

Update `.env`:
```env
DOMAIN_DB_URL=postgresql://memoryservice_readonly:secure_password@localhost:5432/domaindb
```

---

## Integration Architecture

### How It Works

1. **Entity Resolution**: When a user mentions "Acme Corp", the system:
   - Checks `canonical_entities` table for existing mapping
   - If not found, queries domain DB: `SELECT id, name FROM customers WHERE name ILIKE '%Acme Corp%'`
   - Creates canonical entity with `external_ref = {table: 'customers', id: 123}`

2. **Lazy Loading**: Entities are created on-demand (not pre-loaded)

3. **Caching**: `canonical_entities` acts as a cache/index into domain DB

4. **Enrichment**: Domain facts are referenced in `domain_facts_referenced` JSONB field:
   ```json
   {
     "queries": [
       {
         "table": "orders",
         "filter": "customer_id = 123",
         "result_count": 5,
         "sampled_results": [{"order_id": 456, "total": 5000, "status": "shipped"}]
       }
     ]
   }
   ```

### Domain Ontology Table

The `domain_ontology` table stores relationship semantics:

```sql
-- Example: "customer HAS orders"
INSERT INTO app.domain_ontology (
  from_entity_type, relation_type, to_entity_type,
  cardinality, relation_semantics, join_spec
) VALUES (
  'customer', 'has', 'order',
  'one_to_many',
  'Customers can have multiple orders. Use this to find order history.',
  '{"from_table": "customers", "to_table": "orders", "join_on": "customers.id = orders.customer_id"}'::jsonb
);
```

This enables the system to automatically traverse relationships.

---

## Implementation Phases

### Phase 1A-1B (Week 1-4): No Domain DB Required
- Memory system works standalone
- Entities can be created from conversation only
- Domain DB connection not needed

### Phase 1C (Week 5-6): Domain DB Integration
- Connect to domain database
- Implement ontology traversal
- Entity resolution hits domain DB on miss
- Populate `domain_ontology` table

### Future Enhancements (Phase 2+)
- Real-time sync via webhooks
- Domain DB change detection
- Entity deduplication

---

## Testing Without Domain DB

During development, you can:

1. **Use Mock Data**: Create sample tables in the `domain` schema:
   ```sql
   CREATE TABLE domain.customers (
     id SERIAL PRIMARY KEY,
     name TEXT NOT NULL,
     email TEXT,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );

   INSERT INTO domain.customers (name, email) VALUES
     ('Acme Corporation', 'sales@acme.com'),
     ('TechStart Inc', 'hello@techstart.io'),
     ('Global Solutions Ltd', 'info@globalsolutions.com');
   ```

2. **Set `DOMAIN_DB_ENABLED=true`** in `.env`

3. **Configure same database**: Point `DOMAIN_DB_URL` to the same PostgreSQL instance:
   ```env
   DOMAIN_DB_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb
   ```

---

## Verification Checklist

**Before Phase 1C**, ensure:

- [ ] Domain database credentials obtained
- [ ] Read-only user created and tested
- [ ] Schema documentation complete (`docs/domain/SCHEMA.md`)
- [ ] Entity-to-table mapping defined (`docs/domain/ONTOLOGY_MAPPING.md`)
- [ ] Sample queries written for each entity type
- [ ] `DOMAIN_DB_URL` configured in `.env`
- [ ] Connection tested with `psql` or similar tool

---

## Support

For questions about domain database integration:
1. Review `DESIGN.md` Section 4.2 (Domain Database Integration)
2. See `API_DESIGN.md` for entity resolution endpoints
3. Consult `RETRIEVAL_DESIGN.md` for how domain facts affect retrieval

---

**Next Steps**: When you're ready for Phase 1C, the system will automatically use this configuration to integrate with your domain database.
