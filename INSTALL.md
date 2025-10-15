# Installation Guide

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

If you get any errors, install packages individually:

```bash
# Core packages
pip install fastapi==0.115.0
pip install uvicorn[standard]==0.32.0
pip install pydantic==2.9.2
pip install pydantic-settings==2.5.2
pip install python-multipart==0.0.12

# Authentication & Security
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install bcrypt==4.2.0

# Email support (optional)
pip install pydantic[email]
```

### 2. Initialize Database

```bash
python scripts/init_db.py
```

This will:
- Create SQLite database: `nfi_platform.db`
- Run schema migrations
- Create super admin user:
  - Email: `admin@nfigate.com`
  - Password: `Admin123!Change`

### 3. Start the Server

```bash
uvicorn main:app --reload
```

Visit:
- API Documentation: http://localhost:8000/docs
- API Root: http://localhost:8000

## Verify Installation

Test the API is working:

```bash
# Check health
curl http://localhost:8000/health

# Check hierarchy
curl http://localhost:8000/api/v1/rbac/hierarchy

# Login as super admin
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@nfigate.com",
    "password": "Admin123!Change"
  }'
```

## Troubleshooting

### ModuleNotFoundError: No module named 'pydantic_settings'

**Solution**: Install pydantic-settings
```bash
pip install pydantic-settings==2.5.2
```

### ModuleNotFoundError: No module named 'jose'

**Solution**: Install python-jose
```bash
pip install python-jose[cryptography]==3.3.0
```

### ModuleNotFoundError: No module named 'passlib'

**Solution**: Install passlib with bcrypt
```bash
pip install passlib[bcrypt]==1.7.4
pip install bcrypt==4.2.0
```

### Database file not found

**Solution**: Make sure you're running from the project root
```bash
cd nfi-backend
python scripts/init_db.py
```

### Permission denied on database file

**Solution**: Check file permissions
```bash
chmod 644 nfi_platform.db
```

## Next Steps

1. **Change super admin password** via API or directly in database
2. **Configure environment variables** (copy `.env.example` to `.env`)
3. **Test API endpoints** using Swagger UI at http://localhost:8000/docs
4. **Create your first client** and users through the API

## Common Commands

```bash
# Run server with auto-reload (development)
uvicorn main:app --reload

# Run server on different port
uvicorn main:app --reload --port 8080

# Run server with specific host
uvicorn main:app --reload --host 0.0.0.0

# Reset database (WARNING: deletes all data)
rm nfi_platform.db
python scripts/init_db.py
```
