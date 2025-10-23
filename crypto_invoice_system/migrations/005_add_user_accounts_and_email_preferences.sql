-- ============================================================================
-- Migration 005: User Accounts and Email Preferences
-- SaaS Multi-Tenant Support
-- ============================================================================

-- Users/Companies Table (SaaS Customers)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255), -- For future authentication
    is_active BOOLEAN DEFAULT TRUE,
    smtp_host VARCHAR(255) DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER DEFAULT 587,
    smtp_username VARCHAR(255),
    smtp_password VARCHAR(255), -- Encrypted
    smtp_from_email VARCHAR(255),
    smtp_from_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'SaaS customer accounts - companies using the invoice system';
COMMENT ON COLUMN users.email IS 'Primary contact email for the company user';
COMMENT ON COLUMN users.smtp_username IS 'Optional: Company-specific SMTP credentials';

-- Email Notification Preferences
CREATE TABLE IF NOT EXISTS email_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    email_override VARCHAR(255), -- Send to different email than user.email
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, notification_type)
);

COMMENT ON TABLE email_preferences IS 'Email notification preferences per user';
COMMENT ON COLUMN email_preferences.notification_type IS 'Types: invoice_created, payment_detected, payment_confirmed, partial_payment, overpayment, invoice_expired, client_invoice_sent';

-- Notification types enum (for reference)
-- Company notifications:
--   - invoice_created: When company creates new invoice
--   - payment_detected: When payment is first detected
--   - payment_confirmed: When payment is confirmed on blockchain
--   - partial_payment: When underpayment detected
--   - overpayment: When overpayment detected
--   - invoice_expired: When invoice expires without payment
-- Client notifications (sent to invoice.client_contact):
--   - client_invoice_sent: Send invoice to client
--   - client_payment_received: Notify client payment received
--   - client_payment_confirmed: Thank you email to client

-- Add user_id to invoices to link to company user
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);

COMMENT ON COLUMN crypto_invoices.user_id IS 'SaaS user/company that created this invoice';

-- Email delivery log
CREATE TABLE IF NOT EXISTS email_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    invoice_id INTEGER REFERENCES crypto_invoices(id),
    notification_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status VARCHAR(20) NOT NULL, -- sent, failed, bounced
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE email_log IS 'Email delivery tracking and audit trail';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_preferences_user_id ON email_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_email_preferences_type ON email_preferences(notification_type);
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON crypto_invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_email_log_invoice_id ON email_log(invoice_id);
CREATE INDEX IF NOT EXISTS idx_email_log_sent_at ON email_log(sent_at);

-- Insert default user (Delta Energy - the original user)
INSERT INTO users (company_name, contact_name, email, smtp_from_email, smtp_from_name)
VALUES (
    'Delta Energy',
    'Delta CFO Team',
    'cfo@deltaenergy.com',
    'invoices@deltaenergy.com',
    'Delta Energy Invoices'
)
ON CONFLICT (email) DO NOTHING;

-- Insert default email preferences for Delta Energy user
INSERT INTO email_preferences (user_id, notification_type, enabled)
SELECT
    (SELECT id FROM users WHERE email = 'cfo@deltaenergy.com'),
    notification_type,
    TRUE
FROM (VALUES
    ('invoice_created'),
    ('payment_detected'),
    ('payment_confirmed'),
    ('partial_payment'),
    ('overpayment'),
    ('invoice_expired'),
    ('client_invoice_sent')
) AS types(notification_type)
ON CONFLICT (user_id, notification_type) DO NOTHING;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_preferences_updated_at
    BEFORE UPDATE ON email_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
