# Cloudflare D1 Database Setup Guide

This guide explains how to set up and deploy the NFI Platform with Cloudflare D1 database.

## Prerequisites

- Node.js and npm installed
- Cloudflare account
- Wrangler CLI installed globally: `npm install -g wrangler`
- Logged in to Wrangler: `wrangler login`

## Local Development Setup

### 1. Initialize Database Locally

For local development, the API uses SQLite with the same schema as D1:

```bash
# Initialize database and create schema
python scripts/init_db.py
```

This will:
- Create `nfi_platform.db` SQLite database
- Run all schema migrations
- Create a default super admin user

**Default Super Admin Credentials:**
- Email: `admin@nfigate.com`
- Password: `Admin123!Change`

⚠️ **Important**: Change this password immediately!

### 2. Start the Development Server

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload
```

Visit:
- API Docs: http://localhost:8000/docs
- Root: http://localhost:8000

## Cloudflare D1 Production Setup

### 1. Create D1 Database

```bash
# Create the D1 database
wrangler d1 create nfi-platform-db
```

This will output:
```
✅ Successfully created DB 'nfi-platform-db'

[[d1_databases]]
binding = "DB"
database_name = "nfi-platform-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Copy the `database_id` and update it in [wrangler.toml](wrangler.toml)

### 2. Run Database Migrations

```bash
# Execute schema on D1 database
wrangler d1 execute nfi-platform-db --file=database/schema.sql
```

### 3. Set Environment Secrets

```bash
# Set JWT secret key
wrangler secret put SECRET_KEY
# Enter a strong random key (min 32 characters)

# Set KYC provider keys (optional)
wrangler secret put SUMSUB_API_KEY
wrangler secret put SUMSUB_SECRET_KEY
wrangler secret put ONFIDO_API_TOKEN
```

### 4. Deploy to Cloudflare Workers

```bash
# Deploy to production
wrangler deploy

# Or deploy to development
wrangler deploy --env development
```

## D1 Database Commands

### Query the Database

```bash
# Execute a query
wrangler d1 execute nfi-platform-db --command="SELECT * FROM users LIMIT 5"

# Execute from file
wrangler d1 execute nfi-platform-db --file=query.sql
```

### Create Super Admin in Production

```bash
# Create a SQL file with super admin insert
cat > create_admin.sql << 'EOF'
INSERT INTO users (
    id, email, password_hash, first_name, last_name, phone,
    role, tier, status, is_verified, email_verified, created_at, updated_at
) VALUES (
    'super-admin-001',
    'admin@nfigate.com',
    '$2b$12$YOUR_HASHED_PASSWORD_HERE',
    'Super',
    'Admin',
    '+1234567890',
    'super_admin',
    'platform',
    'active',
    1,
    1,
    strftime('%s', 'now') * 1000,
    strftime('%s', 'now') * 1000
);
EOF

# Execute it
wrangler d1 execute nfi-platform-db --file=create_admin.sql
```

**To hash a password:**
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("YourSecurePassword"))
```

### Backup Database

```bash
# Export all data
wrangler d1 export nfi-platform-db --output=backup.sql

# Restore from backup
wrangler d1 execute nfi-platform-db --file=backup.sql
```

### View Database Info

```bash
# List all D1 databases
wrangler d1 list

# Get database info
wrangler d1 info nfi-platform-db
```

## Database Schema

The database includes the following tables:

### Core Tables
- `users` - All platform users (Super Admin, Client, SubClient, End User)
- `clients` - Tier 1: Companies/Banks
- `subclients` - Tier 2: Financial Institutions
- `refresh_tokens` - JWT refresh token storage

### Banking Tables
- `accounts` - User bank accounts
- `transactions` - All financial transactions
- `cards` - Issued cards

### Compliance Tables
- `kyc_verifications` - KYC verification records
- `risk_alerts` - Risk and fraud alerts
- `audit_logs` - System audit trail

### Other Tables
- `notifications` - User notifications
- `api_keys` - API key management

See [database/schema.sql](database/schema.sql) for complete schema.

## Migrations

### Creating a New Migration

1. Create a new SQL file in `database/migrations/`:
```bash
# Example: database/migrations/002_add_user_preferences.sql
CREATE TABLE IF NOT EXISTS user_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    preferences TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

2. Apply locally:
```bash
sqlite3 nfi_platform.db < database/migrations/002_add_user_preferences.sql
```

3. Apply to D1:
```bash
wrangler d1 execute nfi-platform-db --file=database/migrations/002_add_user_preferences.sql
```

## Switching from SQLite to D1

The application automatically detects the environment:

**Local Development** (SQLite):
```python
# Uses nfi_platform.db file
DATABASE_URL = "nfi_platform.db"
```

**Cloudflare Workers** (D1):
```python
# Uses D1 binding from wrangler.toml
# Accessed via env.DB in Workers
```

The database abstraction layer in `app/db/base.py` handles both seamlessly.

## Monitoring & Analytics

### Query Performance

```bash
# Check slow queries (if available)
wrangler d1 execute nfi-platform-db --command="SELECT * FROM sqlite_stat1"
```

### Usage Statistics

View usage in Cloudflare Dashboard:
1. Go to Workers & Pages
2. Select your worker
3. Navigate to Metrics tab
4. View D1 request counts and latency

## Troubleshooting

### Connection Issues

**Error**: "Database not found"
```bash
# Verify database exists
wrangler d1 list

# Check wrangler.toml has correct database_id
cat wrangler.toml | grep database_id
```

### Schema Issues

**Error**: "Table already exists"
- D1 migrations are not idempotent by default
- Use `CREATE TABLE IF NOT EXISTS` in all schema files

### Performance Issues

- **Add indexes** to frequently queried columns
- **Use prepared statements** (handled automatically by our DB layer)
- **Batch operations** when possible
- **Monitor query performance** via Cloudflare dashboard

## Best Practices

1. **Always use transactions** for multi-step operations
2. **Index foreign keys** and frequently queried columns
3. **Store JSON as TEXT** and parse in application
4. **Use INTEGER for timestamps** (milliseconds since epoch)
5. **Implement soft deletes** (status = 'inactive')
6. **Keep queries simple** - D1 is optimized for OLTP
7. **Backup regularly** using `wrangler d1 export`

## Limitations

Cloudflare D1 has some limitations:

- **Database size**: 2 GB per database (as of 2024)
- **Query timeout**: 30 seconds
- **Batch size**: 1000 statements per batch
- **No stored procedures** or triggers
- **Read consistency**: Eventually consistent (< 1 second)

For most use cases, these limits are not an issue. For high-scale operations, consider:
- Sharding by tenant_id
- Using Durable Objects for real-time features
- Implementing caching layer

## Resources

- [D1 Documentation](https://developers.cloudflare.com/d1/)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
- [D1 Pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [D1 Limits](https://developers.cloudflare.com/d1/platform/limits/)

## Support

For issues or questions:
- Email: support@nfigate.com
- GitHub: [Issues](https://github.com/your-org/nfi-platform/issues)
