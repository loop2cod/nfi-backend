INSERT INTO users (
    id, email, password_hash, first_name, last_name, phone,
    role, tier, status, is_verified, email_verified, created_at, updated_at
) VALUES (
    'super-admin-001',
    'admin@nfigate.com',
    'YOUR_BCRYPT_HASH_HERE',
    'Super', 'Admin', '+1234567890',
    'super_admin', 'platform', 'active', 1, 1,
    cast((julianday('now') - 2440587.5) * 86400000 as integer),
    cast((julianday('now') - 2440587.5) * 86400000 as integer)
);