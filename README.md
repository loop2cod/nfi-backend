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

Edit the `.env` file with your Firebase credentials and other settings.

### 5. Create Super Admin User

After configuring Firebase credentials, run the script to create the initial super admin:

```bash
python create_super_admin.py
```

This will create a super admin user with the credentials specified in your `.env` file.

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at:
- **Base URL**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Platform Tier (Tier 0) API Endpoints

### Authentication
- `POST /auth/login` - Login with email/password
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info

### User Management (Super Admin Only)
- `POST /auth/register` - Create new platform user
- `PUT /auth/users/{email}` - Update user information
- `DELETE /auth/users/{email}` - Delete user

### User Management (Admin Roles)
- `GET /auth/users` - List all platform users


## Multi-Tenant Architecture

### Tenant Hierarchy

```
Platform (NFI) - (Platform Owner with master DB)
    ├── Client 1 (Bank A) - (Client with seperate DB)
    │   ├── SubClient 1.1 (Branch 1)
    │   │   ├── End User 1.1.1
    │   │   └── End User 1.1.2
    │   └── SubClient 1.2 (Branch 2)
    │       └── End User 1.2.1
    └── Client 2 (Bank B) - (Client with seperate DB)
        └── End User 2.1.1
        └── SubClient 2.1 (Branch 1)
            └── End User 2.1.1
```


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
