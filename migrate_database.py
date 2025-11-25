"""
Database Migration Script
Migrates existing database to add new fields:
- user_id (NF-MMYYYY###)
- bvnk_customer_id
- bvnk_customer_created_at
- user_counters table
"""

import sqlite3
from datetime import datetime


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
                now = datetime.utcnow()
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

    confirm = input("Do you want to proceed with the migration? (yes/no): ")
    if confirm.lower() == 'yes':
        migrate_database(db_path)
    else:
        print("Migration cancelled.")
