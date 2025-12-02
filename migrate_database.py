"""
Database Migration Script
Migrates existing database to add new fields and tables:
- user_id (NF-MMYYYY###)
- bvnk_customer_id, bvnk_customer_created_at, bvnk_customer_status
- Customer information fields (first_name, last_name, DOB, nationality, phone, address)
- user_counters table
- customer_verification_data table (multi-step verification)
"""

import sqlite3
from datetime import datetime, timezone


def migrate_database(db_path="nfi.db"):
    """Migrate the database to add new fields"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Starting database migration...")

    try:
        # Check if user_counters table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='user_counters'
        """)
        if not cursor.fetchone():
            print("Creating user_counters table...")
            cursor.execute("""
                CREATE TABLE user_counters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_year VARCHAR NOT NULL UNIQUE,
                    counter INTEGER NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX ix_user_counters_month_year ON user_counters (month_year)")
            print("✓ user_counters table created")

        # Check if user_id column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'user_id' not in columns:
            print("Adding user_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN user_id VARCHAR")
            cursor.execute("CREATE UNIQUE INDEX ix_users_user_id ON users (user_id)")
            print("✓ user_id column added")

            # Generate user_ids for existing users
            print("Generating user IDs for existing users...")
            cursor.execute("SELECT id, email FROM users WHERE user_id IS NULL")
            existing_users = cursor.fetchall()

            if existing_users:
                now = datetime.now(timezone.utc)
                month_year = f"{now.month:02d}{now.year}"

                # Get or create counter for current month
                cursor.execute("SELECT counter FROM user_counters WHERE month_year = ?", (month_year,))
                result = cursor.fetchone()

                if result:
                    counter = result[0]
                else:
                    counter = 0
                    cursor.execute("INSERT INTO user_counters (month_year, counter) VALUES (?, ?)", (month_year, counter))

                # Assign user_ids to existing users
                for user_id, email in existing_users:
                    counter += 1
                    new_user_id = f"NF-{month_year}{counter:03d}"
                    cursor.execute("UPDATE users SET user_id = ? WHERE id = ?", (new_user_id, user_id))
                    print(f"  - User {email} assigned ID: {new_user_id}")

                # Update counter
                cursor.execute("UPDATE user_counters SET counter = ? WHERE month_year = ?", (counter, month_year))
                print(f"✓ Generated {len(existing_users)} user IDs")

        if 'bvnk_customer_id' not in columns:
            print("Adding bvnk_customer_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN bvnk_customer_id VARCHAR")
            cursor.execute("CREATE UNIQUE INDEX ix_users_bvnk_customer_id ON users (bvnk_customer_id)")
            print("✓ bvnk_customer_id column added")

        if 'bvnk_customer_created_at' not in columns:
            print("Adding bvnk_customer_created_at column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN bvnk_customer_created_at TIMESTAMP")
            print("✓ bvnk_customer_created_at column added")

        if 'bvnk_customer_status' not in columns:
            print("Adding bvnk_customer_status column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN bvnk_customer_status VARCHAR")
            print("✓ bvnk_customer_status column added")

        if 'first_name' not in columns:
            print("Adding first_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN first_name VARCHAR(100)")
            print("✓ first_name column added")

        if 'last_name' not in columns:
            print("Adding last_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_name VARCHAR(100)")
            print("✓ last_name column added")

        if 'date_of_birth' not in columns:
            print("Adding date_of_birth column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN date_of_birth VARCHAR")
            print("✓ date_of_birth column added")

        if 'nationality' not in columns:
            print("Adding nationality column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN nationality VARCHAR(2)")
            print("✓ nationality column added")

        if 'phone_number' not in columns:
            print("Adding phone_number column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)")
            print("✓ phone_number column added")

        if 'address_line1' not in columns:
            print("Adding address_line1 column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN address_line1 VARCHAR(255)")
            print("✓ address_line1 column added")

        if 'address_line2' not in columns:
            print("Adding address_line2 column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN address_line2 VARCHAR(255)")
            print("✓ address_line2 column added")

        if 'postal_code' not in columns:
            print("Adding postal_code column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN postal_code VARCHAR(20)")
            print("✓ postal_code column added")

        if 'city' not in columns:
            print("Adding city column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN city VARCHAR(100)")
            print("✓ city column added")

        if 'country_code' not in columns:
            print("Adding country_code column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN country_code VARCHAR(2)")
            print("✓ country_code column added")

        if 'state_code' not in columns:
            print("Adding state_code column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN state_code VARCHAR(10)")
            print("✓ state_code column added")

        if 'dfns_user_id' not in columns:
            print("Adding dfns_user_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN dfns_user_id VARCHAR")
            cursor.execute("CREATE UNIQUE INDEX ix_users_dfns_user_id ON users (dfns_user_id)")
            print("✓ dfns_user_id column added")

        if 'preferred_2fa_method' not in columns:
            print("Adding preferred_2fa_method column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_2fa_method VARCHAR")
            print("✓ preferred_2fa_method column added")

        if 'two_fa_methods_priority' not in columns:
            print("Adding two_fa_methods_priority column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN two_fa_methods_priority JSON")
            print("✓ two_fa_methods_priority column added")

        if 'totp_secret' not in columns:
            print("Adding totp_secret column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN totp_secret VARCHAR")
            print("✓ totp_secret column added")

        if 'totp_enabled' not in columns:
            print("Adding totp_enabled column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT 0")
            print("✓ totp_enabled column added")

        # Check if customer_verification_data table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='customer_verification_data'
        """)
        if not cursor.fetchone():
            print("Creating customer_verification_data table...")
            cursor.execute("""
                CREATE TABLE customer_verification_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,

                    -- Step 1: Personal Information
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    date_of_birth DATE,
                    nationality VARCHAR(2),
                    email_address VARCHAR(255),
                    phone_number VARCHAR(20),
                    address_line1 VARCHAR(255),
                    address_line2 VARCHAR(255),
                    postal_code VARCHAR(20),
                    city VARCHAR(100),
                    country_code VARCHAR(2),
                    state_code VARCHAR(10),
                    country VARCHAR(100),

                    -- Step 3: Tax Information
                    tax_identification_number VARCHAR(50),
                    tax_residence_country_code VARCHAR(2),

                    -- Step 4: CDD
                    employment_status VARCHAR(50),
                    source_of_funds VARCHAR(50),
                    pep_status VARCHAR(50),
                    account_purpose VARCHAR(50),
                    expected_monthly_volume_amount DECIMAL(10, 2),
                    expected_monthly_volume_currency VARCHAR(3),

                    -- Progress tracking
                    step_1_completed BOOLEAN DEFAULT 0,
                    step_1_completed_at TIMESTAMP,
                    step_2_completed BOOLEAN DEFAULT 0,
                    step_2_completed_at TIMESTAMP,
                    step_3_completed BOOLEAN DEFAULT 0,
                    step_3_completed_at TIMESTAMP,
                    step_4_completed BOOLEAN DEFAULT 0,
                    step_4_completed_at TIMESTAMP,
                    all_steps_completed BOOLEAN DEFAULT 0,
                    completed_at TIMESTAMP,

                    -- Metadata
                    step_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,

                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("CREATE UNIQUE INDEX ix_customer_verification_data_user_id ON customer_verification_data (user_id)")
            print("✓ customer_verification_data table created")

        # Check if status column exists in wallets table
        cursor.execute("PRAGMA table_info(wallets)")
        wallet_columns = [col[1] for col in cursor.fetchall()]

        # Check if wallets table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='wallets'
        """)
        if not cursor.fetchone():
            print("Creating wallets table...")
            cursor.execute("""
                CREATE TABLE wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_nf_id VARCHAR NOT NULL,
                    currency VARCHAR NOT NULL,
                    address VARCHAR NOT NULL UNIQUE,
                    balance REAL DEFAULT 0.0,
                    available_balance REAL DEFAULT 0.0,
                    frozen_balance REAL DEFAULT 0.0,
                    network VARCHAR NOT NULL,
                    wallet_id VARCHAR NOT NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("CREATE INDEX ix_wallets_user_id ON wallets (user_id)")
            cursor.execute("CREATE INDEX ix_wallets_currency ON wallets (currency)")
            cursor.execute("CREATE INDEX ix_wallets_network ON wallets (network)")
            cursor.execute("CREATE UNIQUE INDEX ix_wallets_address ON wallets (address)")
            print("✓ wallets table created")
        else:
            # Check if user_nf_id column exists in wallets table
            if 'user_nf_id' not in wallet_columns:
                print("Adding user_nf_id column to wallets table...")
                cursor.execute("ALTER TABLE wallets ADD COLUMN user_nf_id VARCHAR")
                print("✓ user_nf_id column added to wallets table")

            if 'status' not in wallet_columns:
                print("Adding status column to wallets table...")
                cursor.execute("ALTER TABLE wallets ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
                print("✓ status column added to wallets table")

        conn.commit()
        print("\n✅ Database migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("NFI Platform Database Migration")
    print("=" * 60)
    print()

    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "nfi.db"

    print(f"Database: {db_path}")
    print()

    # Auto-run migration without confirmation for automated deployment
    migrate_database(db_path)
