from enum import Enum
from typing import List, Optional

class UserRole(str, Enum):
    """User roles in the 4-tier system"""
    # Tier 0: Super Admin (Platform Owner)
    SUPER_ADMIN = "super_admin"
    ADMIN_STAFF = "admin_staff"
    ADMIN_OFFICER = "admin_officer"

    # Tier 1: Client (Company/Bank Admin)
    CLIENT_ADMIN = "client_admin"
    CLIENT_OFFICER = "client_officer"
    CLIENT_STAFF = "client_staff"
    CLIENT_ACCOUNTS = "client_accounts"

    # Tier 2: Sub-Client (Financial Institutions)
    SUBCLIENT_ADMIN = "subclient_admin"
    SUBCLIENT_STAFF = "subclient_staff"

    # Tier 3: End User (Individual Customers)
    END_USER = "end_user"

class UserTier(str, Enum):
    """Hierarchical tiers in the platform"""
    PLATFORM = "platform"      # Tier 0: Super Admin Dashboard
    CLIENT = "client"          # Tier 1: Client Dashboard (Company/Bank)
    SUBCLIENT = "subclient"    # Tier 2: Sub-Client Dashboard (Financial Institution)
    END_USER = "end_user"      # Tier 3: End User Portal

class Permission(str, Enum):
    """Granular permissions for RBAC"""
    # Platform Configuration
    PLATFORM_CONFIG = "platform:config"
    PLATFORM_MONITOR = "platform:monitor"

    # Company/Bank Management
    COMPANY_CREATE = "company:create"
    COMPANY_READ = "company:read"
    COMPANY_UPDATE = "company:update"
    COMPANY_DELETE = "company:delete"

    # Billing & Subscriptions
    BILLING_MANAGE = "billing:manage"
    BILLING_VIEW = "billing:view"

    # KYT Configuration
    KYT_CONFIGURE = "kyt:configure"
    KYT_VIEW = "kyt:view"

    # Sub-Client Management
    SUBCLIENT_CREATE = "subclient:create"
    SUBCLIENT_READ = "subclient:read"
    SUBCLIENT_UPDATE = "subclient:update"
    SUBCLIENT_DELETE = "subclient:delete"

    # End User Management
    ENDUSER_CREATE = "enduser:create"
    ENDUSER_READ = "enduser:read"
    ENDUSER_UPDATE = "enduser:update"
    ENDUSER_DELETE = "enduser:delete"
    ENDUSER_READ_ALL = "enduser:read_all"  # View all end users across sub-clients

    # KYC Management
    KYC_APPROVE = "kyc:approve"
    KYC_REJECT = "kyc:reject"
    KYC_VIEW = "kyc:view"

    # Transaction Management
    TRANSACTION_CREATE = "transaction:create"
    TRANSACTION_READ = "transaction:read"
    TRANSACTION_UPDATE = "transaction:update"
    TRANSACTION_REGISTER = "transaction:register"  # Register transfers

    # Account Management
    ACCOUNT_CREATE = "account:create"
    ACCOUNT_READ = "account:read"
    ACCOUNT_UPDATE = "account:update"
    ACCOUNT_DELETE = "account:delete"

    # Analytics & Reports
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_ADVANCED = "analytics:advanced"
    REPORTS_GENERATE = "reports:generate"

    # Risk & Alerts
    RISK_CONFIGURE = "risk:configure"
    RISK_VIEW = "risk:view"
    ALERT_MANAGE = "alert:manage"

    # API Access
    API_KEYS_MANAGE = "api:keys_manage"
    API_ACCESS = "api:access"

    # Audit & Compliance
    AUDIT_VIEW = "audit:view"
    COMPLIANCE_VIEW = "compliance:view"

# Role to Permission Mapping
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    # Super Admin - Full platform access
    UserRole.SUPER_ADMIN: [
        Permission.PLATFORM_CONFIG,
        Permission.PLATFORM_MONITOR,
        Permission.COMPANY_CREATE,
        Permission.COMPANY_READ,
        Permission.COMPANY_UPDATE,
        Permission.COMPANY_DELETE,
        Permission.BILLING_MANAGE,
        Permission.BILLING_VIEW,
        Permission.KYT_CONFIGURE,
        Permission.SUBCLIENT_CREATE,
        Permission.SUBCLIENT_READ,
        Permission.SUBCLIENT_UPDATE,
        Permission.SUBCLIENT_DELETE,
        Permission.ENDUSER_READ_ALL,
        Permission.KYC_APPROVE,
        Permission.KYC_REJECT,
        Permission.TRANSACTION_REGISTER,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_ADVANCED,
        Permission.REPORTS_GENERATE,
        Permission.RISK_CONFIGURE,
        Permission.ALERT_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.COMPLIANCE_VIEW,
    ],

    # Admin Staff - Limited platform access
    UserRole.ADMIN_STAFF: [
        Permission.PLATFORM_MONITOR,
        Permission.COMPANY_READ,
        Permission.BILLING_VIEW,
        Permission.SUBCLIENT_READ,
        Permission.ENDUSER_READ_ALL,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_VIEW,
        Permission.AUDIT_VIEW,
    ],

    # Admin Officer - Operational access
    UserRole.ADMIN_OFFICER: [
        Permission.PLATFORM_MONITOR,
        Permission.COMPANY_READ,
        Permission.COMPANY_UPDATE,
        Permission.BILLING_VIEW,
        Permission.SUBCLIENT_READ,
        Permission.SUBCLIENT_UPDATE,
        Permission.ENDUSER_READ_ALL,
        Permission.KYC_APPROVE,
        Permission.KYC_REJECT,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_ADVANCED,
        Permission.REPORTS_GENERATE,
        Permission.ALERT_MANAGE,
    ],

    # Client Admin - Company/Bank administrator
    UserRole.CLIENT_ADMIN: [
        Permission.KYT_CONFIGURE,
        Permission.KYT_VIEW,
        Permission.SUBCLIENT_CREATE,
        Permission.SUBCLIENT_READ,
        Permission.SUBCLIENT_UPDATE,
        Permission.SUBCLIENT_DELETE,
        Permission.ENDUSER_READ_ALL,
        Permission.ENDUSER_CREATE,
        Permission.ENDUSER_UPDATE,
        Permission.KYC_APPROVE,
        Permission.KYC_REJECT,
        Permission.KYC_VIEW,
        Permission.TRANSACTION_REGISTER,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_ADVANCED,
        Permission.REPORTS_GENERATE,
        Permission.RISK_CONFIGURE,
        Permission.RISK_VIEW,
        Permission.ALERT_MANAGE,
        Permission.API_KEYS_MANAGE,
        Permission.API_ACCESS,
        Permission.COMPLIANCE_VIEW,
    ],

    # Client Officer - Operations management
    UserRole.CLIENT_OFFICER: [
        Permission.KYT_VIEW,
        Permission.SUBCLIENT_READ,
        Permission.ENDUSER_READ_ALL,
        Permission.ENDUSER_CREATE,
        Permission.ENDUSER_UPDATE,
        Permission.KYC_APPROVE,
        Permission.KYC_REJECT,
        Permission.KYC_VIEW,
        Permission.TRANSACTION_REGISTER,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_VIEW,
        Permission.REPORTS_GENERATE,
        Permission.RISK_VIEW,
        Permission.ALERT_MANAGE,
    ],

    # Client Staff - Basic operations
    UserRole.CLIENT_STAFF: [
        Permission.SUBCLIENT_READ,
        Permission.ENDUSER_READ_ALL,
        Permission.KYC_VIEW,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_VIEW,
        Permission.RISK_VIEW,
    ],

    # Client Accounts - Financial operations
    UserRole.CLIENT_ACCOUNTS: [
        Permission.SUBCLIENT_READ,
        Permission.ENDUSER_READ_ALL,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_REGISTER,
        Permission.ANALYTICS_VIEW,
        Permission.REPORTS_GENERATE,
    ],

    # Sub-Client Admin - Financial institution administrator
    UserRole.SUBCLIENT_ADMIN: [
        Permission.ENDUSER_CREATE,
        Permission.ENDUSER_READ,
        Permission.ENDUSER_UPDATE,
        Permission.KYC_APPROVE,
        Permission.KYC_REJECT,
        Permission.KYC_VIEW,
        Permission.TRANSACTION_REGISTER,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_VIEW,
        Permission.REPORTS_GENERATE,
        Permission.RISK_VIEW,
        Permission.ALERT_MANAGE,
    ],

    # Sub-Client Staff - Customer service
    UserRole.SUBCLIENT_STAFF: [
        Permission.ENDUSER_READ,
        Permission.KYC_VIEW,
        Permission.TRANSACTION_READ,
        Permission.ANALYTICS_VIEW,
        Permission.RISK_VIEW,
    ],

    # End User - Individual customer
    UserRole.END_USER: [
        Permission.ACCOUNT_CREATE,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_UPDATE,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_READ,
    ],
}

def get_user_tier_from_role(role: UserRole) -> UserTier:
    """Get the tier level based on user role"""
    tier_mapping = {
        UserRole.SUPER_ADMIN: UserTier.PLATFORM,
        UserRole.ADMIN_STAFF: UserTier.PLATFORM,
        UserRole.ADMIN_OFFICER: UserTier.PLATFORM,
        UserRole.CLIENT_ADMIN: UserTier.CLIENT,
        UserRole.CLIENT_OFFICER: UserTier.CLIENT,
        UserRole.CLIENT_STAFF: UserTier.CLIENT,
        UserRole.CLIENT_ACCOUNTS: UserTier.CLIENT,
        UserRole.SUBCLIENT_ADMIN: UserTier.SUBCLIENT,
        UserRole.SUBCLIENT_STAFF: UserTier.SUBCLIENT,
        UserRole.END_USER: UserTier.END_USER,
    }
    return tier_mapping.get(role, UserTier.END_USER)

def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions
