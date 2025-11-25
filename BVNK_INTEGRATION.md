# BVNK Integration Guide

## Overview

This document describes the complete integration of BVNK payment services with the NFI Platform, including user registration, KYC verification, and automated customer creation.

## Complete User Flow

```
1. User Sign Up (nfi-end-user)
   ├─> Email & Password Registration
   └─> Unique User ID Generated (NF-MMYYYY###)

2. Authentication
   ├─> JWT Token Issued
   └─> User Dashboard Access

3. KYC Verification (Sumsub)
   ├─> User Initiates KYC
   ├─> Document Upload & Verification
   └─> Sumsub Webhook Notification

4. Automatic BVNK Customer Creation
   ├─> Triggered on KYC Approval (GREEN status)
   ├─> Customer Created in BVNK
   └─> BVNK Customer ID Stored

5. Admin Dashboard (nfi-client-dashboard)
   ├─> View All Customers
   ├─> Filter by KYC/BVNK Status
   └─> Retry Failed BVNK Creations
```

## Architecture Components

### 1. User ID Generation System

**Format:** `NF-MMYYYY###`
- **NF**: Platform prefix
- **MM**: Month (01-12)
- **YYYY**: Year (e.g., 2025)
- **###**: Sequential counter (001-999, resets monthly)

**Examples:**
- First user in January 2025: `NF-012025001`
- Second user in January 2025: `NF-012025002`
- First user in February 2025: `NF-022025001`

**Implementation:**
- `app/models/user_counter.py`: Counter model
- `app/core/user_id_generator.py`: ID generation logic
- Atomic counter increments with database locking

### 2. User Model Updates

**New Fields Added:**
```python
user_id: str                        # Unique user ID (NF-MMYYYY###)
bvnk_customer_id: str              # BVNK customer UUID
bvnk_customer_created_at: datetime # BVNK customer creation timestamp
```

**File:** `app/models/user.py`

### 3. BVNK Client Service

**Features:**
- Hawk Authentication (HMAC-SHA256)
- Customer creation
- Customer retrieval
- Wallet creation
- Idempotency support

**File:** `app/core/bvnk_client.py`

**Configuration:**
```env
BVNK_BASE_URL=https://api.sandbox.bvnk.com  # Sandbox
# BVNK_BASE_URL=https://api.bvnk.com         # Production
BVNK_HAWK_AUTH_ID=your_hawk_auth_id
BVNK_SECRET_KEY=your_secret_key
```

### 4. Webhook Integration

**File:** `app/routers/webhook/sumsub_webhook.py`

**Flow:**
1. Sumsub sends webhook on KYC status change
2. Backend validates webhook signature
3. Updates user verification status
4. If status is "GREEN" (approved):
   - Creates BVNK customer automatically
   - Stores BVNK customer ID
   - Links metadata (user_id, verification_level, verified_at)

**Webhook Events Handled:**
- `applicantReviewed` → BVNK customer creation
- `applicantWorkflowCompleted` → BVNK customer creation
- `applicantPending`, `applicantOnHold`, etc. → Status updates only

### 5. Admin Dashboard Endpoints

**Base Path:** `/admin`

**Endpoints:**

1. **List Customers**
   - `GET /admin/customers`
   - Pagination support (page, size)
   - Filters: search, verification_status, is_verified, has_bvnk_customer
   - Returns: Customer list with user_id, email, KYC status, BVNK status

2. **Get Customer Detail**
   - `GET /admin/customers/{user_id}`
   - Returns: Complete customer information

3. **Customer Statistics**
   - `GET /admin/customers/stats/summary`
   - Returns: Total, verified, pending, failed, BVNK customers count

4. **Retry BVNK Creation**
   - `POST /admin/customers/{user_id}/retry-bvnk`
   - Manually trigger BVNK customer creation for verified users
   - Useful if automatic creation failed

**File:** `app/routers/admin/admin_router.py`

## API Endpoints Reference

### Authentication

**Register New User**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Login**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123"
}

Response:
{
  "two_fa_required": false,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### KYC Verification

**Initialize Sumsub Verification**
```http
POST /auth/sumsub/init
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "level_name": "id-and-liveness"
}

Response:
{
  "success": true,
  "verification_token": "...",
  "applicant_id": "...",
  "sdk_url": "...",
  "config": {...}
}
```

**Check Verification Status**
```http
GET /auth/sumsub/status
Authorization: Bearer {access_token}

Response:
{
  "user_id": 1,
  "is_verified": true,
  "sumsub_status": "completed",
  "email": "user@example.com"
}
```

### Admin Dashboard

**List All Customers**
```http
GET /admin/customers?page=0&size=20&is_verified=true
Authorization: Bearer {admin_access_token}

Response:
{
  "customers": [
    {
      "id": 1,
      "user_id": "NF-012025001",
      "email": "user@example.com",
      "is_active": true,
      "is_verified": true,
      "verification_status": "completed",
      "verification_result": "GREEN",
      "bvnk_customer_id": "uuid-here",
      "bvnk_customer_created_at": "2025-01-24T10:30:00Z",
      "created_at": "2025-01-24T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 0,
  "size": 20,
  "total_pages": 1
}
```

**Get Customer Details**
```http
GET /admin/customers/NF-012025001
Authorization: Bearer {admin_access_token}

Response:
{
  "id": 1,
  "user_id": "NF-012025001",
  "email": "user@example.com",
  "is_active": true,
  "is_verified": true,
  "is_2fa_enabled": false,
  "verification_status": "completed",
  "verification_result": "GREEN",
  "sumsub_applicant_id": "...",
  "bvnk_customer_id": "uuid-here",
  "created_at": "2025-01-24T10:00:00Z"
}
```

**Get Customer Statistics**
```http
GET /admin/customers/stats/summary
Authorization: Bearer {admin_access_token}

Response:
{
  "total_customers": 100,
  "verified_customers": 85,
  "pending_verification": 10,
  "failed_verification": 5,
  "bvnk_customers": 85,
  "active_customers": 95
}
```

**Retry BVNK Customer Creation**
```http
POST /admin/customers/NF-012025001/retry-bvnk
Authorization: Bearer {admin_access_token}

Response:
{
  "success": true,
  "message": "BVNK customer created successfully",
  "bvnk_customer_id": "uuid-here"
}
```

## Database Migration

### For Existing Databases

Run the migration script to add new fields:

```bash
cd /Users/nizam/Documents/Projects/NFI/nfi-backend
python migrate_database.py
```

This will:
1. Create `user_counters` table
2. Add `user_id` column to `users` table
3. Add `bvnk_customer_id` and `bvnk_customer_created_at` columns
4. Generate user IDs for existing users
5. Create indexes for performance

### For Fresh Installation

Simply start the server and tables will be created automatically:

```bash
uvicorn app.main:app --reload
```

## Configuration

### Environment Variables

Update your `.env` file:

```env
# Existing configurations...

# BVNK Configuration
BVNK_BASE_URL=https://api.sandbox.bvnk.com
BVNK_HAWK_AUTH_ID=9QA8UaXlZysiRYmMWizD2bGsa6GJbrYg4SWmQTeFmVBIiIjBLOYrXfiejzpcF6cm
BVNK_SECRET_KEY=4b9au6D65V2aes0VLiW14f4ms9sgdotBCnxVBBNHO9qoUYc0HwkEObmYHrvrOIgL
```

### Production Checklist

Before going to production:

1. ✅ Update `BVNK_BASE_URL` to production: `https://api.bvnk.com`
2. ✅ Use production BVNK credentials
3. ✅ Enable webhook signature verification
4. ✅ Set up proper error monitoring
5. ✅ Configure rate limiting
6. ✅ Set up database backups
7. ✅ Test error handling for BVNK failures

## Error Handling

### BVNK Customer Creation Failures

If BVNK customer creation fails during webhook processing:

1. User's KYC status is still marked as verified ✅
2. `verification_error_message` contains the error
3. Admin can retry creation via: `POST /admin/customers/{user_id}/retry-bvnk`

**Common Failure Scenarios:**
- Network timeout
- BVNK API rate limits
- Invalid customer data
- Duplicate external reference

### User ID Generation Failures

If monthly limit (999) is reached:

- Registration returns error: "Monthly user ID limit reached"
- Solution: Automatically rolls over to next month on first day

## Testing

### Test User Registration Flow

```bash
# 1. Register new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!"}'

# Response includes user_id in token payload

# 2. Get user info
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer {access_token}"

# Response shows user_id: NF-012025001

# 3. Initialize KYC
curl -X POST http://localhost:8000/auth/sumsub/init \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"level_name": "id-and-liveness"}'

# 4. Complete KYC in Sumsub (use their test mode)

# 5. Webhook automatically creates BVNK customer

# 6. Verify BVNK customer created
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer {access_token}"

# Response shows bvnk_customer_id populated
```

### Test Admin Dashboard

```bash
# 1. Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@nfi.com", "password": "admin123"}'

# 2. List all customers
curl -X GET "http://localhost:8000/admin/customers?page=0&size=20" \
  -H "Authorization: Bearer {admin_access_token}"

# 3. Get customer statistics
curl -X GET http://localhost:8000/admin/customers/stats/summary \
  -H "Authorization: Bearer {admin_access_token}"

# 4. Get specific customer
curl -X GET http://localhost:8000/admin/customers/NF-012025001 \
  -H "Authorization: Bearer {admin_access_token}"
```

## Monitoring & Logging

All BVNK operations are logged:

```python
# Success logs
logger.info(f"BVNK customer created for user {user.id}: {user.bvnk_customer_id}")

# Error logs
logger.error(f"Failed to create BVNK customer for user {user.id}: {str(e)}")
```

Monitor these logs for:
- BVNK API failures
- Webhook processing errors
- User ID generation issues
- Authentication failures

## Next Steps

1. **Frontend Integration (nfi-end-user)**
   - Display user_id after registration
   - Show BVNK customer status
   - Integrate Sumsub SDK for KYC

2. **Admin Dashboard (nfi-client-dashboard)**
   - Build customer list UI
   - Add filters and search
   - Display customer statistics
   - Retry button for failed BVNK creations

3. **BVNK Features**
   - Create wallets after customer creation
   - Implement payment flows
   - Add transaction history
   - Set up webhook handlers for payment events

## Support

For issues or questions:
- Check logs in the backend console
- Review BVNK documentation: https://docs.bvnk.com
- Check Sumsub webhook logs: https://cockpit.sumsub.com

---

**Integration completed:** 2025-01-24
**Last updated:** 2025-01-24
