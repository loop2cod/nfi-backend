"""
Test TOTP functionality
"""
import pyotp

# Generate a secret
secret = pyotp.random_base32()
print(f"Secret: {secret}")

# Create TOTP instance
totp = pyotp.TOTP(secret)

# Get current code
current_code = totp.now()
print(f"Current TOTP code: {current_code}")

# Generate provisioning URI
uri = totp.provisioning_uri(name="test@example.com", issuer_name="NFI Platform")
print(f"Provisioning URI: {uri}")

# Test verification
is_valid = totp.verify(current_code, valid_window=2)
print(f"Verification result: {is_valid}")

# Test with wrong code
is_valid_wrong = totp.verify("000000", valid_window=2)
print(f"Verification with wrong code: {is_valid_wrong}")
