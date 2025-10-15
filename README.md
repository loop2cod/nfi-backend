# NFI Platform API

A comprehensive multi-tenant neo banking platform with 4-tier architecture, role-based access control, and complete authentication system.

## Platform Overview

**NFI Platform** is a multi-tenant digital banking infrastructure designed for banks, financial institutions, and fintech companies. It supports a hierarchical 4-tier architecture with granular role-based permissions.

### Architecture Tiers

1. **Platform (Tier 0)**: Super Admin Dashboard
   - Platform owner and administrators
   - System configuration and monitoring
   - Company/Bank onboarding
   - Billing and subscription management

2. **Client (Tier 1)**: Company/Bank Dashboard
   - Company/Bank administrators and staff
   - Sub-client management
   - KYT configuration
   - Risk rules and thresholds
   - End-user oversight

3. **SubClient (Tier 2)**: Financial Institution Dashboard
   - Financial institution operations
   - Customer management
   - Transaction registration
   - Risk alert handling

4. **End User (Tier 3)**: Customer Portal
   - Individual customers
   - Digital account opening
   - KYC verification
   - Wallet management
   - Transactions and payments

## Features

### Authentication & Authorization
- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Role-Based Access Control (RBAC)**: 11 predefined roles with granular permissions
- **Multi-Tenant Support**: Hierarchical tenant management (Platform → Client → SubClient → End User)
- **Password Security**: Bcrypt hashing with configurable token expiration
- **OAuth2 Compatible**: Industry-standard authentication flow

### User Management
- Multi-tier user hierarchy
- Role assignment and permission management
- User status management (active, inactive, suspended, pending_kyc)
- Email verification system
- KYC integration ready (Sumsub & Onfido)

### Banking Operations
- Account Management (savings, checking, business)
- Transaction Processing (deposits, withdrawals, transfers, payments)
- Card Issuance (debit, credit, virtual)
- Multi-currency wallet support

### Security Features
- Token-based authentication (access + refresh tokens)
- Password hashing with bcrypt
- Role and permission-based access control
- Tenant isolation
- Audit trail ready

## User Roles & Permissions

### Platform Tier (Tier 0)
- **super_admin**: Full platform access, system configuration, billing
- **admin_staff**: Platform monitoring and reporting
- **admin_officer**: Operational platform management

### Client Tier (Tier 1)
- **client_admin**: Company/Bank administrator, full client control
- **client_officer**: Operations management, KYC approval
- **client_staff**: Basic operations and reporting
- **client_accounts**: Financial operations and accounting

### SubClient Tier (Tier 2)
- **subclient_admin**: Financial institution administrator
- **subclient_staff**: Customer service and support

### End User Tier (Tier 3)
- **end_user**: Individual customer with personal banking access

## Project Structure

```
nfi-backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── rbac.py           # Role & permission management
│   │   ├── users.py          # User management
│   │   ├── accounts.py       # Account operations
│   │   ├── transactions.py   # Transaction processing
│   │   └── cards.py          # Card management
│   ├── core/
│   │   ├── config.py         # Application settings
│   │   ├── security.py       # JWT & password utilities
│   │   └── dependencies.py   # Auth dependencies & checkers
│   └── models/
│       ├── auth.py           # Auth models (login, tokens)
│       ├── roles.py          # Roles & permissions definitions
│       ├── user.py           # User models with multi-tenant support
│       ├── account.py        # Account models
│       ├── transaction.py    # Transaction models
│       └── card.py           # Card models
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

## Installation

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and update the following:
- `SECRET_KEY`: Generate a secure secret key (min 32 characters)
- `SUMSUB_API_KEY`: Your Sumsub API key (if using KYC)
- `ONFIDO_API_TOKEN`: Your Onfido API token (if using KYC)

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at:
- **Base URL**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register a new user
- `POST /login` - Login and get access tokens
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout and invalidate refresh token
- `POST /change-password` - Change user password
- `GET /me` - Get current user information

### RBAC & Permissions (`/api/v1/rbac`)
- `GET /roles` - Get all available roles
- `GET /permissions` - Get all permissions (Super Admin only)
- `GET /role/{role}/permissions` - Get permissions for a specific role
- `GET /my-permissions` - Get current user's permissions
- `POST /check-permission` - Check if user has a permission
- `GET /access-matrix` - Get complete role-permission matrix
- `GET /hierarchy` - Get platform hierarchy structure

### Users (`/api/v1/users`)
- `POST /` - Create a new user (requires authentication)
- `GET /` - Get all users
- `GET /{user_id}` - Get user by ID
- `PUT /{user_id}` - Update user
- `DELETE /{user_id}` - Delete user

### Accounts (`/api/v1/accounts`)
- `POST /` - Create a new account
- `GET /` - Get all accounts (filter by user_id)
- `GET /{account_id}` - Get account by ID
- `GET /{account_id}/balance` - Get account balance
- `PATCH /{account_id}/freeze` - Freeze account
- `PATCH /{account_id}/activate` - Activate account
- `DELETE /{account_id}` - Close account

### Transactions (`/api/v1/transactions`)
- `POST /` - Create a new transaction
- `GET /` - Get all transactions (filter by account_id)
- `GET /{transaction_id}` - Get transaction by ID
- `GET /reference/{reference_number}` - Get by reference number
- `PATCH /{transaction_id}/cancel` - Cancel transaction

### Cards (`/api/v1/cards`)
- `POST /` - Issue a new card
- `GET /` - Get all cards (filter by account_id)
- `GET /{card_id}` - Get card by ID
- `PATCH /{card_id}/block` - Block a card
- `PATCH /{card_id}/unblock` - Unblock a card
- `DELETE /{card_id}` - Cancel a card

## Usage Examples

### 1. Register a Super Admin User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@nfigate.com",
    "first_name": "Super",
    "last_name": "Admin",
    "phone": "+1234567890",
    "password": "SecurePass123!",
    "role": "super_admin"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@nfigate.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...}
}
```

### 3. Access Protected Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Register a Client Admin

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "bank@example.com",
    "first_name": "Bank",
    "last_name": "Admin",
    "phone": "+1234567891",
    "password": "SecurePass123!",
    "role": "client_admin",
    "tenant_id": "client-uuid-123"
  }'
```

### 5. Register an End User (under SubClient)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567892",
    "password": "SecurePass123!",
    "role": "end_user",
    "parent_id": "subclient-uuid-456"
  }'
```

### 6. Check User Permissions

```bash
curl -X GET "http://localhost:8000/api/v1/rbac/my-permissions" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. Get Platform Hierarchy

```bash
curl -X GET "http://localhost:8000/api/v1/rbac/hierarchy"
```

## Multi-Tenant Architecture

### Tenant Hierarchy

```
Platform (NFI)
    ├── Client 1 (Bank A)
    │   ├── SubClient 1.1 (Branch 1)
    │   │   ├── End User 1.1.1
    │   │   └── End User 1.1.2
    │   └── SubClient 1.2 (Branch 2)
    │       └── End User 1.2.1
    └── Client 2 (Bank B)
        └── SubClient 2.1 (Branch 1)
            └── End User 2.1.1
```

### Tenant Fields

- **tenant_id**: Identifies the Client or SubClient the user belongs to
- **parent_id**: References the parent in the hierarchy
  - SubClient → parent_id = Client ID
  - End User → parent_id = SubClient ID

## Permission System

The platform uses a comprehensive RBAC system with 40+ permissions across categories:

- Platform configuration
- Company/bank management
- Billing & subscriptions
- KYT configuration
- Sub-client management
- End user management
- KYC operations
- Transaction operations
- Account management
- Analytics & reports
- Risk & alerts
- API access
- Audit & compliance

See `/api/v1/rbac/access-matrix` for the complete permission matrix.

## Security Best Practices

### Production Deployment

1. **Change SECRET_KEY**: Generate a strong random secret key
   ```python
   import secrets
   secrets.token_urlsafe(32)
   ```

2. **Use HTTPS**: Always use SSL/TLS in production

3. **Configure CORS**: Restrict CORS origins to your frontend domains
   ```python
   CORS_ORIGINS=["https://yourdomain.com"]
   ```

4. **Database**: Implement proper database with connection pooling

5. **Rate Limiting**: Add rate limiting middleware

6. **Logging**: Implement comprehensive audit logging

7. **MFA**: Consider adding multi-factor authentication

8. **Token Rotation**: Implement token rotation strategy

## Future Enhancements

### Planned Features
- [ ] PostgreSQL/MongoDB database integration
- [ ] Redis caching for tokens
- [ ] Email verification system
- [ ] SMS OTP for MFA
- [ ] Sumsub KYC integration
- [ ] Onfido KYC integration
- [ ] Transaction monitoring & alerts
- [ ] Risk scoring engine
- [ ] Audit logging system
- [ ] Rate limiting
- [ ] API key management
- [ ] Webhook system
- [ ] Real-time notifications
- [ ] Advanced analytics

### Database Schema (When Implementing)
- Users table with multi-tenant support
- Tenants table (Clients & SubClients)
- Accounts, Transactions, Cards tables
- KYC verifications table
- Audit logs table
- Refresh tokens table

## Support & Documentation

- **Interactive API Docs**: http://localhost:8000/docs
- **Email**: support@nfigate.com
- **Website**: www.nfigate.com

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Important Notes

⚠️ **Current Implementation**:
- Uses in-memory storage (replace with database for production)
- No email verification implemented yet
- KYC providers not integrated yet
- No rate limiting
- No audit logging
- Basic error handling

**For Production**:
- Implement proper database (PostgreSQL recommended)
- Add Redis for token storage and caching
- Implement email verification
- Add rate limiting middleware
- Implement comprehensive audit logging
- Add monitoring and alerting
- Use environment-based configuration
- Implement proper error handling and logging
- Add unit and integration tests
- Set up CI/CD pipeline

## Acknowledgments

Built with FastAPI, Pydantic, and Python-JOSE for a secure, modern neo banking platform.
