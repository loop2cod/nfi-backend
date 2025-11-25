#!/bin/bash

# Quick test script for admin creation
echo "Testing admin creation..."
echo ""

# Test with a test email
python create_admin.py test-admin@nfi.com TestPassword123

echo ""
echo "If successful, try logging in with:"
echo "  Email: test-admin@nfi.com"
echo "  Password: TestPassword123"
