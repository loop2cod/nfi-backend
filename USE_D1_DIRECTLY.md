# Using Cloudflare D1 Directly with NFI Platform

This guide shows you how to connect your NFI Platform FastAPI backend **directly** to Cloudflare D1 (no SQLite).

## 🎯 Quick Start

### Step 1: Create D1 Database

```bash
wrangler d1 create nfi-platform-db
```

Save the output - you'll need the `database_id`.

### Step 2: Run Migrations

```bash
wrangler d1 execute nfi-platform-db --file=database/schema.sql
```

### Step 3: Get Cloudflare API Credentials

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Click on your profile → **API Tokens**
3. Click **Create Token**
4. Use template: **Edit Cloudflare Workers**
5. Add **D1 Edit** permission
6. Copy the generated token

Get your Account ID:
```bash
wrangler whoami
```

### Step 4: Create Super Admin in D1

```bash
# Generate password hash
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('Admin123!Change'))"
```

Copy the hash, then create `create_admin.sql`:

```sql
INSERT INTO users (
    id, email, password_hash, first_name, last_name, phone,
    role, tier, status, is_verified, email_verified, created_at, updated_at
) VALUES (
    'super-admin-001',
    'admin@nfigate.com',
    '$2b$12$YOUR_HASH_HERE',  -- Replace with your hash
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
```

Execute it:
```bash
wrangler d1 execute nfi-platform-db --file=create_admin.sql
```

### Step 5: Configure Environment Variables

Create `.env` file:

```env
# Application
APP_NAME=NFI Platform API
APP_VERSION=1.0.0
DEBUG=False

# Security
SECRET_KEY=your-super-secret-key-min-32-chars-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database - USE D1
DATABASE_TYPE=d1
D1_ACCOUNT_ID=your-cloudflare-account-id
D1_DATABASE_ID=your-d1-database-id-from-step-1
D1_API_TOKEN=your-cloudflare-api-token-from-step-3

# CORS
CORS_ORIGINS=["*"]

# KYC (Optional)
SUMSUB_API_KEY=your_sumsub_key
SUMSUB_SECRET_KEY=your_sumsub_secret
ONFIDO_API_TOKEN=your_onfido_token
```

### Step 6: Install Dependencies

```bash
pip install requests
```

### Step 7: Start the Server

```bash
uvicorn main:app --reload
```

You should see:
```
🚀 Starting NFI Platform API...
📊 Connected to Cloudflare D1 via HTTP API
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 8: Test the Connection

```bash
# Check health
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nfigate.com","password":"Admin123!Change"}'
```

## ✅ You're Now Using D1 Directly!

Your FastAPI backend is now connected to Cloudflare D1 via HTTP API. No SQLite needed!

## 🔄 Switching Between SQLite and D1

You can easily switch between local SQLite and Cloudflare D1:

**Use SQLite (Local Development):**
```env
DATABASE_TYPE=sqlite
DATABASE_URL=nfi_platform.db
```

**Use D1 (Production/Cloud):**
```env
DATABASE_TYPE=d1
D1_ACCOUNT_ID=xxx
D1_DATABASE_ID=xxx
D1_API_TOKEN=xxx
```

## 📊 Managing D1 Database

### View Data

```bash
# List all users
wrangler d1 execute nfi-platform-db \
  --command="SELECT id, email, role, status FROM users"

# Count users by role
wrangler d1 execute nfi-platform-db \
  --command="SELECT role, COUNT(*) as count FROM users GROUP BY role"

# View recent transactions
wrangler d1 execute nfi-platform-db \
  --command="SELECT * FROM transactions ORDER BY created_at DESC LIMIT 10"
```

### Backup Database

```bash
# Export all data
wrangler d1 export nfi-platform-db --output=backup-$(date +%Y%m%d).sql

# Restore from backup
wrangler d1 execute nfi-platform-db --file=backup-20240101.sql
```

### Execute Custom Queries

```bash
# Create a query file
echo "SELECT * FROM users WHERE role='super_admin'" > query.sql

# Execute it
wrangler d1 execute nfi-platform-db --file=query.sql
```

## 🚀 Deployment Options

### Option 1: Deploy FastAPI to Cloud Platform

Deploy your FastAPI app to any platform:
- **Railway**: `railway up`
- **Fly.io**: `fly deploy`
- **Render**: Push to GitHub
- **AWS/Azure/GCP**: Use Docker

Set environment variables with D1 credentials.

### Option 2: Hybrid Architecture (Recommended)

```
┌─────────────────┐
│ Cloudflare      │
│ Workers (Edge)  │  ← Fast endpoints (auth, public APIs)
│ + D1 Direct     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FastAPI Backend │  ← Complex logic, admin operations
│ + D1 HTTP API   │
└─────────────────┘
```

### Option 3: Local Development + D1

Run FastAPI locally, connect to remote D1:
```bash
# In .env
DATABASE_TYPE=d1
D1_ACCOUNT_ID=xxx
D1_DATABASE_ID=xxx
D1_API_TOKEN=xxx

# Start server
uvicorn main:app --reload
```

## ⚡ Performance Considerations

### D1 HTTP API Latency

- **Local SQLite**: ~1-5ms queries
- **D1 HTTP API**: ~50-200ms queries (depends on location)

### Optimization Tips

1. **Use connection pooling** (handled automatically)
2. **Batch operations** when possible
3. **Cache frequently accessed data**
4. **Use indexes** on commonly queried fields
5. **Consider edge deployment** for lowest latency

### When to Use Each

**Use SQLite (Local):**
- Development and testing
- Fast iteration
- Offline work

**Use D1 (Production):**
- Production deployments
- Multi-region access
- Scalability needs
- Data persistence

## 🔒 Security Best Practices

1. **Never commit** `.env` file
2. **Rotate API tokens** regularly
3. **Use environment-specific** tokens (dev/prod)
4. **Limit token permissions** to D1 only
5. **Enable IP restrictions** on Cloudflare API tokens
6. **Monitor API usage** in Cloudflare dashboard

## 🐛 Troubleshooting

### "D1 configuration incomplete"

**Solution**: Check your `.env` file has all three D1 variables:
```env
D1_ACCOUNT_ID=...
D1_DATABASE_ID=...
D1_API_TOKEN=...
```

### "API token invalid"

**Solution**: Verify token has D1 permissions:
1. Go to Cloudflare Dashboard → API Tokens
2. Click **View** on your token
3. Ensure **D1 Edit** permission is enabled
4. Generate new token if needed

### "Database not found"

**Solution**: Verify database_id is correct:
```bash
wrangler d1 list
```

### Slow query performance

**Solution**:
1. Add indexes to frequently queried columns
2. Consider caching layer (Redis)
3. Use batch operations for multiple queries
4. Deploy closer to D1 (Cloudflare Workers)

## 📚 Resources

- [Cloudflare D1 Docs](https://developers.cloudflare.com/d1/)
- [D1 REST API](https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
- [API Token Permissions](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)

## 💡 Next Steps

1. ✅ Test all API endpoints with D1
2. ✅ Set up monitoring and alerts
3. ✅ Implement caching layer
4. ✅ Add rate limiting
5. ✅ Deploy to production platform
6. ✅ Set up automated backups
7. ✅ Configure CI/CD pipeline

## Need Help?

- Email: support@nfigate.com
- Check logs: `tail -f logs/nfi-platform.log`
- D1 metrics: Cloudflare Dashboard → D1 → Metrics
