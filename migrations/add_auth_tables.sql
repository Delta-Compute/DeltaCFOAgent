-- ====================================================================
-- Delta CFO Agent - Authentication System Migration
-- ====================================================================
-- Description: Adds Firebase authentication support with multi-tenant
--              user management, role-based access control, and audit logging
-- Date: 2025-10-27
-- Version: 1.0
-- ====================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================================================
-- ENUM TYPES
-- ====================================================================

-- User type enumeration
CREATE TYPE user_type_enum AS ENUM (
    'fractional_cfo',
    'cfo_assistant',
    'tenant_admin',
    'employee'
);

-- User role within tenant
CREATE TYPE user_role_enum AS ENUM (
    'owner',
    'admin',
    'cfo',
    'cfo_assistant',
    'employee'
);

-- Payment ownership
CREATE TYPE payment_owner_enum AS ENUM (
    'cfo',
    'tenant'
);

-- Subscription status
CREATE TYPE subscription_status_enum AS ENUM (
    'trial',
    'active',
    'suspended',
    'cancelled'
);

-- Invitation status
CREATE TYPE invitation_status_enum AS ENUM (
    'pending',
    'accepted',
    'expired',
    'revoked'
);

-- ====================================================================
-- TABLE: users
-- ====================================================================
-- Stores user accounts with Firebase authentication integration

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    user_type user_type_enum NOT NULL,
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    invited_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- Indexes for performance
    CONSTRAINT users_firebase_uid_key UNIQUE (firebase_uid),
    CONSTRAINT users_email_key UNIQUE (email)
);

CREATE INDEX idx_users_firebase_uid ON users(firebase_uid);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ====================================================================
-- TABLE: tenant_configuration (ALTER EXISTING)
-- ====================================================================
-- Add authentication-related fields to existing tenant_configuration table

-- Check if columns exist before adding them
DO $$
BEGIN
    -- Add created_by_user_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='created_by_user_id') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
    END IF;

    -- Add current_admin_user_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='current_admin_user_id') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN current_admin_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
    END IF;

    -- Add payment_owner column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='payment_owner') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN payment_owner payment_owner_enum DEFAULT 'tenant';
    END IF;

    -- Add payment_method_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='payment_method_id') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN payment_method_id VARCHAR(255);
    END IF;

    -- Add subscription_status column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='subscription_status') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN subscription_status subscription_status_enum DEFAULT 'trial';
    END IF;

    -- Add subscription_started_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='subscription_started_at') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN subscription_started_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add subscription_ends_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tenant_configuration' AND column_name='subscription_ends_at') THEN
        ALTER TABLE tenant_configuration
        ADD COLUMN subscription_ends_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- ====================================================================
-- TABLE: tenant_users
-- ====================================================================
-- Junction table linking users to tenants with roles and permissions

CREATE TABLE IF NOT EXISTS tenant_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenant_configuration(id) ON DELETE CASCADE,
    role user_role_enum NOT NULL,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    added_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT tenant_users_unique_user_tenant UNIQUE (user_id, tenant_id)
);

CREATE INDEX idx_tenant_users_user_id ON tenant_users(user_id);
CREATE INDEX idx_tenant_users_tenant_id ON tenant_users(tenant_id);
CREATE INDEX idx_tenant_users_role ON tenant_users(role);
CREATE INDEX idx_tenant_users_is_active ON tenant_users(is_active);
CREATE INDEX idx_tenant_users_permissions ON tenant_users USING gin(permissions);

-- ====================================================================
-- TABLE: user_permissions
-- ====================================================================
-- Reference table defining available permissions

CREATE TABLE IF NOT EXISTS user_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_key VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_permissions_category ON user_permissions(category);
CREATE INDEX idx_user_permissions_key ON user_permissions(permission_key);

-- Insert default permissions
INSERT INTO user_permissions (permission_key, permission_name, description, category) VALUES
    -- Transaction permissions
    ('transactions.view', 'View Transactions', 'View transaction data and history', 'transactions'),
    ('transactions.create', 'Create Transactions', 'Create new transactions', 'transactions'),
    ('transactions.edit', 'Edit Transactions', 'Edit existing transactions', 'transactions'),
    ('transactions.delete', 'Delete Transactions', 'Delete transactions', 'transactions'),
    ('transactions.export', 'Export Transactions', 'Export transaction data', 'transactions'),

    -- Invoice permissions
    ('invoices.view', 'View Invoices', 'View invoice data', 'invoices'),
    ('invoices.create', 'Create Invoices', 'Create new invoices', 'invoices'),
    ('invoices.edit', 'Edit Invoices', 'Edit existing invoices', 'invoices'),
    ('invoices.delete', 'Delete Invoices', 'Delete invoices', 'invoices'),
    ('invoices.approve', 'Approve Invoices', 'Approve invoices for payment', 'invoices'),

    -- User management permissions
    ('users.view', 'View Users', 'View user list and details', 'users'),
    ('users.invite', 'Invite Users', 'Invite new users to the system', 'users'),
    ('users.manage', 'Manage Users', 'Edit and deactivate users', 'users'),

    -- Report permissions
    ('reports.view', 'View Reports', 'View financial reports and dashboards', 'reports'),
    ('reports.generate', 'Generate Reports', 'Generate custom reports', 'reports'),
    ('reports.export', 'Export Reports', 'Export reports to various formats', 'reports'),

    -- Settings permissions
    ('settings.view', 'View Settings', 'View tenant settings', 'settings'),
    ('settings.edit', 'Edit Settings', 'Modify tenant settings', 'settings'),
    ('settings.billing', 'Manage Billing', 'Manage billing and payment settings', 'settings'),

    -- Account permissions
    ('accounts.view', 'View Accounts', 'View bank accounts and wallets', 'accounts'),
    ('accounts.manage', 'Manage Accounts', 'Add, edit, and remove accounts', 'accounts')
ON CONFLICT (permission_key) DO NOTHING;

-- ====================================================================
-- TABLE: user_invitations
-- ====================================================================
-- Tracks email invitations sent to new users

CREATE TABLE IF NOT EXISTS user_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    invited_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenant_configuration(id) ON DELETE CASCADE,
    user_type user_type_enum NOT NULL,
    role user_role_enum NOT NULL,
    invitation_token UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    status invitation_status_enum DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    accepted_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Additional data for invitation
    invitation_data JSONB DEFAULT '{}'
);

CREATE INDEX idx_user_invitations_email ON user_invitations(email);
CREATE INDEX idx_user_invitations_token ON user_invitations(invitation_token);
CREATE INDEX idx_user_invitations_status ON user_invitations(status);
CREATE INDEX idx_user_invitations_tenant_id ON user_invitations(tenant_id);
CREATE INDEX idx_user_invitations_invited_by ON user_invitations(invited_by_user_id);

-- ====================================================================
-- TABLE: audit_log
-- ====================================================================
-- Comprehensive audit trail for user actions

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    tenant_id VARCHAR(50) REFERENCES tenant_configuration(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Additional context
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_tenant_id ON audit_log(tenant_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource_type ON audit_log(resource_type);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_changes ON audit_log USING gin(changes);

-- ====================================================================
-- FUNCTIONS & TRIGGERS
-- ====================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically expire invitations
CREATE OR REPLACE FUNCTION expire_old_invitations()
RETURNS void AS $$
BEGIN
    UPDATE user_invitations
    SET status = 'expired'
    WHERE status = 'pending'
    AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================
-- VIEWS
-- ====================================================================

-- View for active user-tenant relationships
CREATE OR REPLACE VIEW v_active_tenant_users AS
SELECT
    u.id AS user_id,
    u.firebase_uid,
    u.email,
    u.display_name,
    u.user_type,
    tu.tenant_id,
    tc.company_name AS tenant_name,
    tu.role,
    tu.permissions,
    tu.added_at
FROM users u
JOIN tenant_users tu ON u.id = tu.user_id
JOIN tenant_configuration tc ON tu.tenant_id = tc.id
WHERE u.is_active = true AND tu.is_active = true;

-- View for pending invitations
CREATE OR REPLACE VIEW v_pending_invitations AS
SELECT
    ui.id,
    ui.email,
    ui.user_type,
    ui.role,
    ui.tenant_id,
    tc.company_name AS tenant_name,
    u.display_name AS invited_by_name,
    u.email AS invited_by_email,
    ui.sent_at,
    ui.expires_at,
    EXTRACT(EPOCH FROM (ui.expires_at - CURRENT_TIMESTAMP)) AS seconds_until_expiry
FROM user_invitations ui
JOIN users u ON ui.invited_by_user_id = u.id
JOIN tenant_configuration tc ON ui.tenant_id = tc.id
WHERE ui.status = 'pending'
AND ui.expires_at > CURRENT_TIMESTAMP;

-- ====================================================================
-- COMMENTS
-- ====================================================================

COMMENT ON TABLE users IS 'User accounts with Firebase authentication';
COMMENT ON TABLE tenant_users IS 'User-tenant relationships with roles and permissions';
COMMENT ON TABLE user_permissions IS 'Available permissions reference table';
COMMENT ON TABLE user_invitations IS 'Email invitations for new users';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all user actions';

COMMENT ON COLUMN users.firebase_uid IS 'Firebase user unique identifier';
COMMENT ON COLUMN users.user_type IS 'User type: fractional_cfo, cfo_assistant, tenant_admin, or employee';
COMMENT ON COLUMN tenant_users.role IS 'User role within the tenant: owner, admin, cfo, cfo_assistant, or employee';
COMMENT ON COLUMN tenant_users.permissions IS 'JSONB object of specific permissions';
COMMENT ON COLUMN user_invitations.invitation_token IS 'Unique token for invitation acceptance';
COMMENT ON COLUMN audit_log.changes IS 'JSONB object capturing before/after state';

-- ====================================================================
-- COMPLETION MESSAGE
-- ====================================================================

DO $$
BEGIN
    RAISE NOTICE '======================================';
    RAISE NOTICE 'Authentication schema migration completed successfully!';
    RAISE NOTICE '======================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users';
    RAISE NOTICE '  - tenant_users';
    RAISE NOTICE '  - user_permissions';
    RAISE NOTICE '  - user_invitations';
    RAISE NOTICE '  - audit_log';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables modified:';
    RAISE NOTICE '  - tenant_configuration (added auth fields)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Create initial admin user';
    RAISE NOTICE '  2. Configure Firebase credentials';
    RAISE NOTICE '  3. Test authentication flow';
    RAISE NOTICE '======================================';
END $$;
