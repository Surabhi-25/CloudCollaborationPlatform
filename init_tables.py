import psycopg2
from psycopg2 import sql

# --- ⚠️ REQUIRED: REPLACE THESE PLACEHOLDERS WITH YOUR ACTUAL RDS DETAILS ⚠️ ---
DB_HOST = "mp-database.c5iswawek3lu.ap-south-1.rds.amazonaws.com"  # The Endpoint from your RDS console
DB_USER = "postgres"                  # e.g., 'postgres' or 'admin'
DB_PASS = "postgres123"                  # The password you set during creation
DB_NAME = "postgres"                    # e.g., 'postgres' or 'main'
DB_PORT = 5432                                    # Default port for PostgreSQL
# --------------------------------------------------------------------------------

TABLE_CREATION_SQL = """
-- 1. USERS Table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    team_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. TEAMS Table
CREATE TABLE IF NOT EXISTS teams (
    team_id VARCHAR(36) PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    owner_user_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. FILES Table
CREATE TABLE IF NOT EXISTS files (
    file_id VARCHAR(36) PRIMARY KEY,
    team_id VARCHAR(36) NOT NULL,
    owner_user_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    current_version_id INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    acl JSONB
);

-- 4. VERSIONS Table
CREATE TABLE IF NOT EXISTS versions (
    file_id VARCHAR(36) NOT NULL,
    version_id INT NOT NULL,
    PRIMARY KEY (file_id, version_id),
    s3_key VARCHAR(512) NOT NULL,
    mime_type VARCHAR(100),
    uploaded_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

def create_tables():
    """Connects to RDS and executes the table creation script."""
    conn = None
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            sslmode='require' # RDS often requires SSL
        )

        # Create a new cursor
        cur = conn.cursor()

        # Execute the entire script
        print("Executing SQL script to create tables...")
        cur.execute(TABLE_CREATION_SQL)

        # Commit the changes to the database
        conn.commit()
        print("✅ SUCCESS: All four tables (users, teams, files, versions) created successfully.")

        # Close the cursor and connection
        cur.close()

    except psycopg2.OperationalError as e:
        print("\n❌ CONNECTION ERROR: Please check your configuration:")
        print("  - Did you open port 5432 in your RDS Security Group for your IP?")
        print(f"  - Database Endpoint/Credentials correct: {e}")
        return
    except Exception as e:
        print(f"\n❌ ERROR: An unexpected error occurred: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_tables()