-- NFI Platform Database Schema for Cloudflare D1
-- Multi-Tenant Neo Banking Platform

-- ====================
-- TENANTS & ORGANIZATIONS
-- ====================

-- Clients (Tier 1: Companies/Banks)
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company_type TEXT NOT NULL, -- 'bank', 'fintech', 'financial_institution'
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    country TEXT,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'inactive', 'suspended'
    subscription_plan TEXT,
    billing_email TEXT,
    api_key TEXT UNIQUE,
    settings TEXT, -- JSON string for KYT settings, risk thresholds, etc.
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- SubClients (Tier 2: Financial Institutions/Branches)
CREATE TABLE IF NOT EXISTS subclients (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    name TEXT NOT NULL,
    branch_code TEXT,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    settings TEXT, -- JSON string
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- ====================
-- USERS (All Tiers)
-- ====================

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,

    -- Role & Hierarchy
    role TEXT NOT NULL, -- 'super_admin', 'client_admin', 'subclient_admin', 'end_user', etc.
    tier TEXT NOT NULL, -- 'platform', 'client', 'subclient', 'end_user'
    tenant_id TEXT, -- client_id or subclient_id depending on role
    parent_id TEXT, -- hierarchical parent reference

    -- Status & Verification
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'inactive', 'suspended', 'pending_kyc', 'kyc_rejected'
    is_verified INTEGER NOT NULL DEFAULT 0,
    email_verified INTEGER NOT NULL DEFAULT 0,

    -- KYC
    kyc_status TEXT, -- 'pending', 'approved', 'rejected'
    kyc_provider TEXT, -- 'sumsub', 'onfido'
    kyc_reference TEXT,
    kyc_completed_at INTEGER,

    -- Security
    last_login INTEGER,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until INTEGER,

    -- Metadata
    metadata TEXT, -- JSON string for additional data
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_parent_id ON users(parent_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- ====================
-- AUTHENTICATION
-- ====================

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    revoked_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ====================
-- ACCOUNTS
-- ====================

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    account_number TEXT UNIQUE NOT NULL,
    account_type TEXT NOT NULL, -- 'savings', 'checking', 'business'
    currency TEXT NOT NULL DEFAULT 'USD',
    balance TEXT NOT NULL DEFAULT '0.00', -- Store as TEXT to prevent precision issues
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'frozen', 'closed'
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_account_number ON accounts(account_number);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);

-- ====================
-- TRANSACTIONS
-- ====================

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    reference_number TEXT UNIQUE NOT NULL,
    from_account_id TEXT NOT NULL,
    to_account_id TEXT,
    amount TEXT NOT NULL, -- Store as TEXT for precision
    transaction_type TEXT NOT NULL, -- 'deposit', 'withdrawal', 'transfer', 'payment'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'cancelled'
    description TEXT,

    -- Risk & Monitoring
    risk_score REAL,
    flagged INTEGER DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at INTEGER,

    metadata TEXT, -- JSON string
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    completed_at INTEGER,

    FOREIGN KEY (from_account_id) REFERENCES accounts(id),
    FOREIGN KEY (to_account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_from_account ON transactions(from_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_to_account ON transactions(to_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_reference ON transactions(reference_number);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_flagged ON transactions(flagged);

-- ====================
-- CARDS
-- ====================

CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    card_number TEXT UNIQUE NOT NULL, -- Encrypted
    card_number_last4 TEXT NOT NULL,
    cvv TEXT NOT NULL, -- Encrypted
    card_type TEXT NOT NULL, -- 'debit', 'credit', 'virtual'
    card_name TEXT,
    expiry_month INTEGER NOT NULL,
    expiry_year INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'blocked', 'expired', 'cancelled'
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cards_account_id ON cards(account_id);
CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status);
CREATE INDEX IF NOT EXISTS idx_cards_last4 ON cards(card_number_last4);

-- ====================
-- KYC VERIFICATIONS
-- ====================

CREATE TABLE IF NOT EXISTS kyc_verifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL, -- 'sumsub', 'onfido'
    verification_id TEXT, -- External provider's verification ID
    status TEXT NOT NULL, -- 'pending', 'approved', 'rejected', 'requires_review'
    verification_type TEXT, -- 'identity', 'address', 'document'

    -- Documents
    documents TEXT, -- JSON array of document info

    -- Results
    result_code TEXT,
    result_message TEXT,
    risk_score REAL,

    -- Review
    reviewed_by TEXT,
    reviewed_at INTEGER,
    rejection_reason TEXT,

    metadata TEXT, -- JSON string
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    completed_at INTEGER,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status ON kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_kyc_provider ON kyc_verifications(provider);

-- ====================
-- AUDIT LOGS
-- ====================

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    action TEXT NOT NULL, -- 'login', 'create_user', 'approve_kyc', etc.
    resource_type TEXT, -- 'user', 'account', 'transaction', etc.
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    status TEXT, -- 'success', 'failure'
    error_message TEXT,
    metadata TEXT, -- JSON string
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);

-- ====================
-- NOTIFICATIONS
-- ====================

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL, -- 'email', 'sms', 'push', 'in_app'
    channel TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'read'
    priority TEXT DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    metadata TEXT, -- JSON string
    sent_at INTEGER,
    read_at INTEGER,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);

-- ====================
-- RISK ALERTS
-- ====================

CREATE TABLE IF NOT EXISTS risk_alerts (
    id TEXT PRIMARY KEY,
    transaction_id TEXT,
    user_id TEXT,
    alert_type TEXT NOT NULL, -- 'high_amount', 'suspicious_pattern', 'sanction_match', etc.
    severity TEXT NOT NULL, -- 'low', 'medium', 'high', 'critical'
    status TEXT NOT NULL DEFAULT 'open', -- 'open', 'investigating', 'resolved', 'false_positive'
    description TEXT NOT NULL,
    risk_score REAL,

    -- Assignment
    assigned_to TEXT,
    assigned_at INTEGER,

    -- Resolution
    resolved_by TEXT,
    resolved_at INTEGER,
    resolution_notes TEXT,

    metadata TEXT, -- JSON string
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_transaction ON risk_alerts(transaction_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_user ON risk_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_status ON risk_alerts(status);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_severity ON risk_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_created_at ON risk_alerts(created_at);

-- ====================
-- API KEYS
-- ====================

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    key_name TEXT NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    api_secret TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'revoked', 'expired'
    permissions TEXT, -- JSON array of permissions
    rate_limit INTEGER DEFAULT 1000, -- requests per hour
    expires_at INTEGER,
    last_used_at INTEGER,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_client_id ON api_keys(client_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
