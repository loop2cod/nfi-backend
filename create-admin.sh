#!/bin/bash

# NFI Platform - Create Admin User
# Quick script to create an admin user for the dashboard

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "  NFI Platform - Create Admin User"
echo "============================================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating virtual environment..."

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
        echo ""
    else
        echo -e "${RED}❌ Error: venv not found. Please run: python -m venv venv${NC}"
        exit 1
    fi
fi

# Check if arguments provided
if [ $# -eq 0 ]; then
    # Interactive mode
    echo "Enter admin credentials:"
    echo ""
    read -p "Email: " email
    read -s -p "Password: " password
    echo ""
    echo ""

    # Run the Python script
    python create_admin.py "$email" "$password"
elif [ $# -eq 2 ]; then
    # Non-interactive mode
    python create_admin.py "$1" "$2"
else
    echo -e "${RED}Usage:${NC}"
    echo "  ./create-admin.sh                    # Interactive mode"
    echo "  ./create-admin.sh email password     # Non-interactive mode"
    echo ""
    echo -e "${YELLOW}Example:${NC}"
    echo "  ./create-admin.sh admin@nfi.com SecurePass123"
    exit 1
fi
