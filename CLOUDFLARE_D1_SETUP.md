# Cloudflare D1 Setup - Direct Connection

This guide shows how to use Cloudflare D1 directly (not SQLite) for your NFI Platform.

## Prerequisites

- Cloudflare account with Workers and D1 enabled
- Wrangler CLI: `npm install -g wrangler`
- Wrangler login: `wrangler login`

## Step 1: Create D1 Database

```bash
# Create D1 database
wrangler d1 create nfi-platform-db
```

Output will show:
```
✅ Successfully created DB 'nfi-platform-db'

[[d1_databases]]
binding = "DB"
database_name = "nfi-platform-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Copy the `database_id`** - you'll need it!

## Step 2: Update wrangler.toml

Update the `database_id` in [wrangler.toml](wrangler.toml):

```toml
[[d1_databases]]
binding = "DB"
database_name = "nfi-platform-db"
database_id = "YOUR-DATABASE-ID-HERE"  # Paste your ID here
```

## Step 3: Run Database Migrations

```bash
# Execute schema on D1
wrangler d1 execute nfi-platform-db --file=database/schema.sql
```

This creates all tables in your D1 database.

## Step 4: Create Super Admin User

Since D1 is remote, you need to create the admin user through D1:

```bash
# Generate password hash locally
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('Admin123!Change'))"
```

Copy the hash, then create SQL file:

```bash
cat > create_admin.sql << 'EOF'
INSERT INTO users (
    id, email, password_hash, first_name, last_name, phone,
    role, tier, status, is_verified, email_verified, created_at, updated_at
) VALUES (
    'super-admin-001',
    'admin@nfigate.com',
    'YOUR_BCRYPT_HASH_HERE',
    'Super',
    'Admin',
    '+1234567890',
    'super_admin',
    'platform',
    'active',
    1,
    1,
    cast((julianday('now') - 2440587.5) * 86400000 as integer),
    cast((julianday('now') - 2440587.5) * 86400000 as integer)
);
EOF
```

Execute it:
```bash
wrangler d1 execute nfi-platform-db --file=create_admin.sql
```

## Step 5: Set Environment Secrets

```bash
# Set JWT secret
wrangler secret put SECRET_KEY
# Enter a strong random 32+ character key

# Optional: KYC provider keys
wrangler secret put SUMSUB_API_KEY
wrangler secret put SUMSUB_SECRET_KEY
wrangler secret put ONFIDO_API_TOKEN
```

## Step 6: Deploy to Cloudflare Workers

### Option A: Deploy with FastAPI (Using Workers for Platforms)

For FastAPI to work on Cloudflare Workers, you need to use the Workers for Platforms or Pages Functions approach.

**Note**: Direct FastAPI deployment to Workers is experimental. Consider these approaches:

1. **Use Cloudflare Pages Functions** (Recommended)
2. **Use Workers with a Python ASGI adapter**
3. **Deploy to another platform** (Railway, Fly.io, etc.) with D1 HTTP API

### Option B: Deploy with D1 HTTP API

You can keep FastAPI running anywhere and connect to D1 via HTTP API:

```bash
# Get D1 HTTP API token
wrangler d1 info nfi-platform-db
```

Update your `.env`:
```env
DATABASE_URL=d1-http
D1_DATABASE_ID=your-database-id
D1_ACCOUNT_ID=your-account-id
D1_API_TOKEN=your-api-token
```

### Option C: Use Cloudflare Workers directly (JavaScript/TypeScript)

For production use, consider rewriting critical endpoints in Workers:

```typescript
// worker.ts
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const db = env.DB;

    // Example: Login endpoint
    if (request.url.endsWith('/api/v1/auth/login')) {
      const { email, password } = await request.json();

      // Query D1
      const user = await db.prepare(
        'SELECT * FROM users WHERE email = ?'
      ).bind(email).first();

      // ... handle login logic

      return new Response(JSON.stringify({ token: '...' }));
    }

    return new Response('Not found', { status: 404 });
  }
};
```

## Using D1 from Python (Current Setup)

### For Local Development:
The app uses SQLite as a local D1 equivalent:
```bash
python scripts/init_db.py
uvicorn main:app --reload
```

### For Production with D1:

1. **Deploy FastAPI to a platform that supports Python** (Railway, Fly.io, Render)
2. **Connect to D1 via HTTP API** using `wrangler d1 execute` commands or D1 HTTP API
3. **Use Cloudflare Tunnel** to connect your server to D1

## D1 HTTP API Connection

To connect directly to D1 from Python:

```python
import requests

class D1HTTPClient:
    def __init__(self, account_id, database_id, api_token):
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"

    def execute(self, sql, params=None):
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        data = {"sql": sql}
        if params:
            data["params"] = params

        response = requests.post(self.base_url, json=data, headers=headers)
        return response.json()
```

## Recommended Production Architecture

For a production NFI Platform with D1:

```
┌─────────────────────────────────────────────────┐
│         Cloudflare Workers (Edge)               │
│  - Authentication endpoints                     │
│  - Public-facing APIs                           │
│  - Direct D1 access                            │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         FastAPI Backend (Python)                │
│  - Complex business logic                       │
│  - Admin operations                             │
│  - Background jobs                              │
│  - Connect to D1 via HTTP API                   │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         Cloudflare D1 Database                  │
│  - Primary data store                           │
│  - Multi-tenant data                            │
└─────────────────────────────────────────────────┘
```

## Query D1 Database

```bash
# Query users
wrangler d1 execute nfi-platform-db \
  --command="SELECT * FROM users LIMIT 5"

# Check tables
wrangler d1 execute nfi-platform-db \
  --command="SELECT name FROM sqlite_master WHERE type='table'"

# Count users by role
wrangler d1 execute nfi-platform-db \
  --command="SELECT role, COUNT(*) as count FROM users GROUP BY role"
```

## Export/Backup D1 Database

```bash
# Export to SQL file
wrangler d1 export nfi-platform-db --output=backup.sql

# Restore from backup
wrangler d1 execute nfi-platform-db --file=backup.sql
```

## Limitations & Considerations

1. **D1 is in beta** - APIs may change
2. **Query timeout**: 30 seconds max
3. **Database size**: 2 GB limit per database
4. **No connection pooling** - D1 handles this automatically
5. **Eventually consistent** reads (< 1 second)
6. **Python Workers support** is limited - consider Workers (JS/TS) for edge

## Next Steps

1. **Create D1 database**: `wrangler d1 create nfi-platform-db`
2. **Run migrations**: `wrangler d1 execute nfi-platform-db --file=database/schema.sql`
3. **Create admin user**: Follow Step 4 above
4. **Choose deployment strategy**: Workers (JS), FastAPI + D1 HTTP API, or hybrid
5. **Deploy**: Based on your chosen architecture

## Resources

- [Cloudflare D1 Docs](https://developers.cloudflare.com/d1/)
- [D1 REST API](https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database)
- [Workers Python Docs](https://developers.cloudflare.com/workers/languages/python/)
- [Workers for Platforms](https://developers.cloudflare.com/cloudflare-for-platforms/workers-for-platforms/)

## Support

For assistance: support@nfigate.com
