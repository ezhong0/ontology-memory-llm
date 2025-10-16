#!/usr/bin/env bash
#
# Clean Test Data
#
# Removes all test data from database to ensure clean E2E test runs.
# This is a workaround for test fixture transaction rollback not working
# properly when API code commits the session.
#
# Usage: ./scripts/clean_test_data.sh

set -e

echo "🧹 Cleaning test data from database..."

PGPASSWORD=memorypass psql -h localhost -U memoryuser -d memorydb <<EOF
DO \$\$
BEGIN
  -- Clean domain tables
  TRUNCATE TABLE domain.payments CASCADE;
  TRUNCATE TABLE domain.invoices CASCADE;
  TRUNCATE TABLE domain.work_orders CASCADE;
  TRUNCATE TABLE domain.sales_orders CASCADE;
  TRUNCATE TABLE domain.tasks CASCADE;
  TRUNCATE TABLE domain.customers CASCADE;

  -- Clean app tables
  TRUNCATE TABLE app.memory_conflicts CASCADE;
  TRUNCATE TABLE app.memory_summaries CASCADE;
  TRUNCATE TABLE app.procedural_memories CASCADE;
  TRUNCATE TABLE app.semantic_memories CASCADE;
  TRUNCATE TABLE app.episodic_memories CASCADE;
  TRUNCATE TABLE app.entity_aliases CASCADE;
  TRUNCATE TABLE app.canonical_entities CASCADE;
  TRUNCATE TABLE app.chat_events CASCADE;

  RAISE NOTICE 'Test data cleaned successfully';
END \$\$;
EOF

echo "✅ Test data cleaned successfully"
echo ""
echo "You can now run E2E tests:"
echo "  poetry run pytest tests/e2e/test_scenarios.py -v"
