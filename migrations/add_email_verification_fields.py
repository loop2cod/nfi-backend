"""
Migration script to add email verification fields to users table
For SQLite database
"""
import sqlite3
from datetime import datetime

DATABASE_PATH = "./nfi.db"


def migrate():
    """Add email verification fields to users table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        # Add email_verification_otp column if it doesn't exist
        if "email_verification_otp" not in columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN email_verification_otp TEXT
            """)
            print("✓ Added email_verification_otp column")
        else:
            print("- email_verification_otp column already exists")

        # Add email_verification_otp_expiry column if it doesn't exist
        if "email_verification_otp_expiry" not in columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN email_verification_otp_expiry TIMESTAMP
            """)
            print("✓ Added email_verification_otp_expiry column")
        else:
            print("- email_verification_otp_expiry column already exists")

        # Add email_verified_at column if it doesn't exist
        if "email_verified_at" not in columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN email_verified_at TIMESTAMP
            """)
            print("✓ Added email_verified_at column")
        else:
            print("- email_verified_at column already exists")

        conn.commit()
        print(f"\n✅ Migration completed successfully at {datetime.now()}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise

    finally:
        conn.close()


def rollback():
    """
    Note: SQLite doesn't support DROP COLUMN in older versions
    If rollback is needed, you may need to recreate the table
    """
    print("⚠️  SQLite doesn't support DROP COLUMN easily.")
    print("To rollback, you would need to:")
    print("1. Create a new table without these columns")
    print("2. Copy data from old table")
    print("3. Drop old table")
    print("4. Rename new table")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
