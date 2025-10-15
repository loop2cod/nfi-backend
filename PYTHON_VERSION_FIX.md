# Python Version Compatibility Fix

## Problem
Python 3.14 is too new. FastAPI and related packages don't support it yet.

## Solution: Use Python 3.11 or 3.12

### Option 1: Install Python 3.12 (Recommended)

1. **Download Python 3.12**
   - Go to: https://www.python.org/downloads/
   - Download Python 3.12.x (latest stable)
   - During installation, CHECK "Add Python to PATH"

2. **Create new virtual environment with Python 3.12**
   ```bash
   # Navigate to project
   cd C:\Users\loopcod\Documents\projects\nfi\nfi-backend

   # Remove old venv
   rmdir /s venv

   # Create new venv with Python 3.12
   py -3.12 -m venv venv

   # Activate it
   venv\Scripts\activate

   # Verify Python version
   python --version
   # Should show: Python 3.12.x

   # Install dependencies
   pip install -r requirements.txt

   # Run server
   uvicorn main:app --reload
   ```

### Option 2: Use Python 3.11

If you have Python 3.11 installed:

```bash
# Remove old venv
rmdir /s venv

# Create new venv with Python 3.11
py -3.11 -m venv venv

# Activate
venv\Scripts\activate

# Install
pip install -r requirements.txt

# Run
uvicorn main:app --reload
```

### Option 3: Quick Docker Setup (No Python install needed)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Run:
```bash
docker build -t nfi-backend .
docker run -p 8000:8000 nfi-backend
```

## Why Python 3.14 Doesn't Work

- **Released**: October 2024 (very new!)
- **FastAPI**: Not tested with 3.14 yet
- **Pydantic**: Core dependency breaks on 3.14
- **typing-extensions**: Internal changes in 3.14 break compatibility

## Recommended Python Versions

✅ **Python 3.12** - Best choice (latest stable)
✅ **Python 3.11** - Also great
✅ **Python 3.10** - Stable, widely supported
⚠️ **Python 3.14** - Too new, avoid for production
⚠️ **Python 3.9** - Works but getting old

## After Switching Python Version

Once you have Python 3.11 or 3.12:

```bash
# 1. Activate venv
venv\Scripts\activate

# 2. Initialize database
python scripts/init_db.py

# 3. Start server
uvicorn main:app --reload

# 4. Open browser
# http://localhost:8000/docs
```

## Quick Test

```bash
# Login as super admin
curl -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@nfigate.com\",\"password\":\"Admin123!Change\"}"
```

## Need Help?

If you can't install Python 3.12:
1. Use Python 3.11 if available
2. Use Docker (no Python install needed)
3. Use online IDE (Replit, Gitpod)

The backend is fully ready to run - just needs compatible Python version!
