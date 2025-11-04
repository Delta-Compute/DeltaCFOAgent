-- Migration: Add Payment Proof Tracking Columns to Invoices Table
-- Purpose: Enable storage of payment receipts and payment confirmation data
-- Date: 2025-11-04

-- Add payment status column first (if it doesn't exist)
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_status TEXT DEFAULT 'pending';

-- Add payment tracking columns to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_date TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_proof_path TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_method TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_confirmation_number TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_notes TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_proof_uploaded_at TIMESTAMP;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_proof_uploaded_by TEXT;

-- Create index for faster queries on payment status
CREATE INDEX IF NOT EXISTS idx_invoices_payment_status ON invoices(payment_status);

-- Create index for payment date queries
CREATE INDEX IF NOT EXISTS idx_invoices_payment_date ON invoices(payment_date);

-- Create index for finding invoices with/without payment proof
CREATE INDEX IF NOT EXISTS idx_invoices_payment_proof ON invoices(payment_proof_path);

-- Rollback script (commented out - use for rollback if needed)
/*
ALTER TABLE invoices DROP COLUMN IF EXISTS payment_date;
ALTER TABLE invoices DROP COLUMN IF EXISTS payment_proof_path;
ALTER TABLE invoices DROP COLUMN IF EXISTS payment_method;
ALTER TABLE invoices DROP COLUMN IF EXISTS payment_confirmation_number;
ALTER TABLE invoices DROP COLUMN IF EXISTS payment_notes;
ALTER TABLE invoices DROP COLUMN IF NOT EXISTS payment_proof_uploaded_at;
ALTER TABLE invoices DROP COLUMN IF NOT EXISTS payment_proof_uploaded_by;
DROP INDEX IF EXISTS idx_invoices_payment_status;
DROP INDEX IF EXISTS idx_invoices_payment_date;
DROP INDEX IF EXISTS idx_invoices_payment_proof;
*/
