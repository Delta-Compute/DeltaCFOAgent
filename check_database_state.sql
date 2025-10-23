-- ============================================================================
-- Database State Checker for DeltaCFOAgent
-- Run this to diagnose what's missing in your database
-- ============================================================================

\echo '════════════════════════════════════════════════════════════════════════════'
\echo 'DELTACFOAGENT DATABASE DIAGNOSTIC'
\echo '════════════════════════════════════════════════════════════════════════════'
\echo ''

-- Check if new tables exist
\echo '1. Checking if required tables exist...'
\echo ''

SELECT
    CASE
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tenant_configuration')
        THEN '✅ tenant_configuration EXISTS'
        ELSE '❌ tenant_configuration MISSING'
    END as status;

SELECT
    CASE
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wallet_addresses')
        THEN '✅ wallet_addresses EXISTS'
        ELSE '❌ wallet_addresses MISSING'
    END as status;

SELECT
    CASE
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bank_accounts')
        THEN '✅ bank_accounts EXISTS'
        ELSE '❌ bank_accounts MISSING'
    END as status;

SELECT
    CASE
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'homepage_content')
        THEN '✅ homepage_content EXISTS'
        ELSE '❌ homepage_content MISSING'
    END as status;

\echo ''
\echo '2. Checking Delta tenant configuration...'
\echo ''

SELECT
    CASE
        WHEN EXISTS (SELECT FROM tenant_configuration WHERE tenant_id = 'delta')
        THEN '✅ Delta tenant configured'
        ELSE '❌ Delta tenant NOT configured'
    END as status;

-- Show tenant data if exists
SELECT
    'Company: ' || company_name as info
FROM tenant_configuration
WHERE tenant_id = 'delta';

SELECT
    'Tagline: ' || company_tagline as info
FROM tenant_configuration
WHERE tenant_id = 'delta';

\echo ''
\echo '3. Checking business entities...'
\echo ''

SELECT
    COUNT(*) || ' active business entities found' as status
FROM business_entities
WHERE active = TRUE;

-- List entities
SELECT
    '  • ' || name || ' (' || entity_type || ')' as entity
FROM business_entities
WHERE active = TRUE
ORDER BY name;

\echo ''
\echo '4. Checking accounts data...'
\echo ''

SELECT
    COUNT(*) || ' bank accounts found' as status
FROM bank_accounts
WHERE tenant_id = 'delta' AND status != 'closed';

SELECT
    COUNT(*) || ' crypto wallets found' as status
FROM wallet_addresses
WHERE tenant_id = 'delta' AND is_active = TRUE;

\echo ''
\echo '5. Checking transaction data...'
\echo ''

SELECT
    COUNT(*) || ' total transactions' as status
FROM transactions
WHERE tenant_id = 'delta';

SELECT
    COALESCE(SUM(amount), 0)::NUMERIC(15,2) || ' total revenue' as status
FROM transactions
WHERE tenant_id = 'delta' AND amount > 0;

SELECT
    COALESCE(SUM(ABS(amount)), 0)::NUMERIC(15,2) || ' total expenses' as status
FROM transactions
WHERE tenant_id = 'delta' AND amount < 0;

\echo ''
\echo '════════════════════════════════════════════════════════════════════════════'
\echo 'DIAGNOSIS COMPLETE'
\echo '════════════════════════════════════════════════════════════════════════════'
\echo ''
\echo 'If you see any ❌ MISSING status above, you need to apply the schema:'
\echo '  psql -h HOST -U USER -d delta_cfo < postgres_unified_schema.sql'
\echo ''
\echo 'If business entities = 0, the seed data was not loaded.'
\echo 'If transactions = 0, you need to upload transaction files.'
\echo ''
