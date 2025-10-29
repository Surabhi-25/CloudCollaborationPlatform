import psycopg2
import os

# --- Configuration (Make sure these match your RDS settings) ---
# It's best practice to load these from environment variables in production,
# but for local testing, you can set them here temporarily.

# Note: We confirmed DB_NAME should be 'postgres' for connection
DB_HOST = "artifactlogs.c5iswawek3lu.ap-south-1.rds.amazonaws.com" # Replace with your actual endpoint if different
DB_NAME = "postgres"  
DB_USER = "postgres"  # Your master username
DB_PASSWORD = "postgres123" # ⚠️ REPLACE THIS
DB_PORT = "5432"
# -------------------------------------------------------------

def create_artifact_logs_table():
    """
    Connects to the RDS database and creates the artifact_logs table 
    for tracking S3 upload activity.
    """
    conn = None
    try:
        # Establish connection
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()

        print(f"✅ Connected successfully to RDS instance: {DB_HOST}")
        
        # SQL to create the artifact_logs table and necessary indexes
        create_table_sql = """
        -- Table for logging all S3 file operations, like uploads and downloads
        CREATE TABLE IF NOT EXISTS artifact_logs (
            log_id SERIAL PRIMARY KEY,
            artifact_name VARCHAR(255) NOT NULL,
            s3_key VARCHAR(512) NOT NULL,
            bucket_name VARCHAR(255) NOT NULL,
            upload_user_id VARCHAR(100) NOT NULL,
            upload_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Index for faster lookups based on the user
        CREATE INDEX IF NOT EXISTS idx_log_upload_user_id ON artifact_logs (upload_user_id);
        
        -- Index for faster lookups based on the S3 key
        CREATE INDEX IF NOT EXISTS idx_log_s3_key ON artifact_logs (s3_key);
        """
        
        cur.execute(create_table_sql)
        print("🎉 Successfully created or verified 'artifact_logs' table and indexes.")

        cur.close()

    except psycopg2.Error as e:
        print(f"\n❌ DATABASE ERROR: Could not create tables.")
        print(f"Details: {e}")
        # Hint for common connection errors
        if 'timed out' in str(e) or 'refused' in str(e):
             print("\nSuggestion: Check your RDS Security Group and Public Accessibility settings.")
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        # Close the connection
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    create_artifact_logs_table()
