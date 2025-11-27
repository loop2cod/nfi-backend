# DFNS Wallet Integration Setup Guide

## Overview

DFNS provides Wallet-as-a-Service infrastructure for creating and managing blockchain wallets. This guide walks through the complete setup process to enable automatic USDT and USDC wallet creation for verified users.

## Prerequisites

- DFNS account (sign up at https://dfns.co/)
- Access to DFNS Dashboard
- Understanding of public/private key cryptography

## Step 1: Create DFNS Organization

1. Sign up at https://dashboard.dfns.io/
2. Create a new organization
3. Note your **Organization ID** (format: `or-xxxxx-xxxxx-xxxxx`)

## Step 2: Create Service Account

Service accounts enable programmatic API access without user interaction.

### Via DFNS Dashboard:

1. Navigate to **Settings** → **Service Accounts**
2. Click **Create Service Account**
3. Provide a name (e.g., "NFI Backend Service")
4. Set permissions:
   - `Wallets:Create` - Required for wallet creation
   - `Wallets:Read` - Required for wallet queries
   - `Auth:Login:Delegated` - Required for user delegation
5. Set token TTL (recommended: 90-180 days for production)
6. **Generate Key Pair** (see Step 3)

### Important Notes:

- Service Account ID format: `us-xxxxx-xxxxx-xxxxx`
- Access token is shown only once - save it securely
- Service accounts require their own credentials (public/private key pair)

## Step 3: Generate Key Pair for Service Account

You need a signing key pair (public/private) for the service account to sign API requests.

### Option A: Generate via DFNS Dashboard

1. During service account creation, click "Generate Key Pair"
2. Download the private key (PEM format)
3. Save the Credential ID (format: `km-xxxxx-xxxxx`)
4. **IMPORTANT:** Store the private key securely (AWS Secrets Manager, etc.)

### Option B: Generate Manually (using OpenSSL)

```bash
# Generate private key
openssl genrsa -out dfns-private-key.pem 2048

# Extract public key
openssl rsa -in dfns-private-key.pem -pubout -out dfns-public-key.pem

# Register public key in DFNS Dashboard under service account
```

## Step 4: Configure Environment Variables

Update your `.env` file with the following DFNS credentials:

```env
# DFNS Configuration
DFNS_BASE_URL=https://api.dfns.io  # or https://api.uae.dfns.io for UAE region
DFNS_ORG_ID=or-xxxxx-xxxxx-xxxxx  # Your organization ID
DFNS_CRED_ID=km-xxxxx-xxxxx  # Credential ID from key pair
DFNS_AUTH_TOKEN=<service_account_access_token>  # Service account token (long-lived)

# Private key (multi-line PEM format)
DFNS_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...full PEM content...
-----END RSA PRIVATE KEY-----"
```

### Required Credentials Explained:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `DFNS_BASE_URL` | API endpoint URL | Use `https://api.dfns.io` for production |
| `DFNS_ORG_ID` | Organization identifier | From DFNS Dashboard → Settings |
| `DFNS_CRED_ID` | Credential ID for signing | Generated when creating key pair |
| `DFNS_AUTH_TOKEN` | Service account access token | Shown once during service account creation |
| `DFNS_PRIVATE_KEY` | Private key for signing requests | Downloaded PEM file content |

## Step 5: Verify Configuration

Test your DFNS configuration by starting the backend:

```bash
cd nfi-backend
python -m uvicorn app.main:app --reload
```

Check the startup logs:
- ✅ Success: "Dfns client initialized successfully"
- ❌ Error: "Failed to initialize Dfns client" → Check credentials

## Step 6: Test Wallet Creation

### Automatic Creation (on KYC completion):

1. User completes all 4 verification steps
2. System automatically creates USDT and USDC wallets
3. Check logs for: "USDT wallet created" and "USDC wallet created"

### Manual Creation (Admin Dashboard):

1. Navigate to Customer Details page
2. Click "Create Wallets" button (if not auto-created)
3. Verify wallet addresses are generated

### API Testing:

```bash
# Create wallets for a verified customer (admin endpoint)
curl -X POST http://localhost:8000/admin/customers/{user_id}/create-wallets \
  -H "Authorization: Bearer <admin_token>"

# Expected response:
{
  "success": true,
  "message": "Successfully created/retrieved 2 wallet(s)",
  "wallets": [
    {
      "currency": "USDT",
      "address": "0x...",
      "network": "EthereumSepolia",
      "wallet_id": "wa-...",
      "status": "CREATED"
    },
    {
      "currency": "USDC",
      "address": "0x...",
      "network": "EthereumSepolia",
      "wallet_id": "wa-...",
      "status": "CREATED"
    }
  ]
}
```

## Step 7: Production Deployment

### Security Best Practices:

1. **Never commit private keys to git**
   - Use environment variables or secret management services
   - Add `.env` to `.gitignore`

2. **Use AWS Secrets Manager or equivalent**
   ```python
   import boto3

   def get_dfns_credentials():
       client = boto3.client('secretsmanager')
       secret = client.get_secret_value(SecretId='dfns-credentials')
       return json.loads(secret['SecretString'])
   ```

3. **Rotate service account tokens regularly**
   - Set shorter TTL for production (90 days)
   - Create rotation process before expiry

4. **Monitor API usage**
   - Track wallet creation requests
   - Set up alerts for failures
   - Monitor DFNS API rate limits

### Network Configuration:

For production, update network from testnet to mainnet:

```python
# In wallets_router.py and verification_router.py
STABLECOIN_NETWORKS = {
    "USDT": "Ethereum",  # Mainnet
    "USDC": "Ethereum",  # Mainnet
}
```

## Troubleshooting

### Error: "Failed to initialize Dfns client"

**Cause:** Invalid credentials or malformed private key

**Solutions:**
1. Verify PEM format is correct (includes BEGIN/END markers)
2. Check credential ID matches the key pair
3. Ensure no extra whitespace in environment variables
4. Test key pair with OpenSSL: `openssl rsa -in key.pem -check`

### Error: "No challenge received"

**Cause:** Service account lacks required permissions

**Solutions:**
1. Add `Wallets:Create` permission to service account
2. Verify service account is active (not suspended)
3. Check token hasn't expired

### Error: "Could not deserialize key data"

**Cause:** Private key format issue or wrong password

**Solutions:**
1. Ensure key is in PEM format (not DER or other formats)
2. Remove any password protection from the key
3. Re-generate key pair if necessary

### Mock Wallets (Development Mode)

If DFNS is not configured, the system falls back to creating mock wallets:
- Addresses are randomly generated (not real blockchain addresses)
- Wallet IDs prefixed with "mock-"
- Useful for development/testing without DFNS account

## API Endpoints Summary

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/wallets/create` | POST | Create wallets for current user | User Token |
| `/admin/customers/{user_id}/create-wallets` | POST | Create wallets for any customer | Admin Token |
| `/wallets` | GET | List user's wallets | User Token |

## Supported Networks and Currencies

| Currency | Testnet Network | Mainnet Network |
|----------|----------------|-----------------|
| USDT | EthereumSepolia | Ethereum |
| USDC | EthereumSepolia | Ethereum |

## Additional Resources

- **DFNS Documentation:** https://docs.dfns.co/
- **Service Account Management:** https://docs.dfns.co/d/api-docs/authentication/service-account-management
- **API Authentication:** https://docs.dfns.co/d/advanced-topics/authentication/authentication-authorization
- **Credentials Guide:** https://docs.dfns.co/d/advanced-topics/authentication/credentials
- **Signing Requests:** https://docs.dfns.co/developers/guides/signing-requests

## Support

For issues with DFNS setup:
1. Check DFNS documentation
2. Contact DFNS support: support@dfns.co
3. Review backend logs for detailed error messages

---

**Last Updated:** 2025-01-27
**Author:** NFI Platform Team



{"supportedCredentialKinds":[{"kind":"RecoveryKey","factor":"either","requiresSecondFactor":false},{"kind":"Fido2","factor":"either","requiresSecondFactor":false}],"challenge":"eyJpZCI6ImNoLTAxamIyLWYxdjBoLWU3MW9taDlpcjlmMmEzMGciLCJub25jZSI6Im5vLTAxamIyLWYxdjBoLWU3MW9taDlrMzg1bDkzaWwifQ","challengeIdentifier":"eyJ0eXAiOiJKV1QiLCJhbGciOiJFZERTQSJ9.eyJpc3MiOiJhdXRoLmRmbnMuaW8iLCJhdWQiOiJkZm5zOmF1dGg6dXNlciIsInN1YiI6Im9yLTAxajk1LXI5cTJlLWUxanIyNDJhaWJhbW05cHQiLCJqdGkiOiJ1ai0wMWpiMi1mMXYwaC1lNzFvbWg5cXA4cWhzMWlwIiwiaHR0cHM6Ly9jdXN0b20vdXNlcm5hbWUiOiJhZG1pbkBuZmlnYXRlLmNvbSIsImh0dHBzOi8vY3VzdG9tL2FwcF9tZXRhZGF0YSI6eyJ1c2VySWQiOiJ1cy0wMWo5NS1yOXE3OS1lOWJiMGJmMTI4cjRxb2pmIiwib3JnSWQiOiJvci0wMWo5NS1yOXEyZS1lMWpyMjQyYWliYW1tOXB0IiwidG9rZW5LaW5kIjoiVGVtcCIsImNoYWxsZW5nZSI6ImV5SnBaQ0k2SW1Ob0xUQXhhbUl5TFdZeGRqQm9MV1UzTVc5dGFEbHBjamxtTW1Fek1HY2lMQ0p1YjI1alpTSTZJbTV2TFRBeGFtSXlMV1l4ZGpCb0xXVTNNVzl0YURsck16ZzFiRGt6YVd3aWZRIn0sImlhdCI6MTc2NDI0MDcxOCwiZXhwIjoxNzY0MjQxNjE4fQ.4UMVNByCvCuu2RTKy-eCqhYV5ZDp1VBh49Jzwgf4LuQxFrWHSIBtDPtzl8NKQ6fi60EVP3srwhAm691FgCjgDw","externalAuthenticationUrl":"","allowCredentials":{"webauthn":[{"type":"public-key","id":"km-kLXJhaJWe72_wikUOJg"}],"key":[]},"attestation":"direct","userVerification":"required"}