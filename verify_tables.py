import psycopg2
import os

# ----------------------------------------------------------------------
# ⚠️ ACTION REQUIRED: UPDATE THESE CREDENTIALS 
# ----------------------------------------------------------------------
# Use the same credentials you used in your init_tables.py script.

DB_HOST = "mp-database.c5iswawek3lu.ap-south-1.rds.amazonaws.com"  # The Endpoint from your RDS console
DB_USER = "postgres"                  # e.g., 'postgres' or 'admin'
DB_PASSWORD = "postgres123"                  # The password you set during creation
DB_NAME = "postgres"                    # e.g., 'postgres' or 'main'
DB_PORT = 5432 
# ----------------------------------------------------------------------

def verify_tables():
    """Connects to the RDS database and prints a list of all existing tables."""
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
        
        # Create a cursor object to execute SQL commands
        cur = conn.cursor()
        
        # SQL query to select all user-created table names in the 'public' schema
        print(f"✅ Connection successful to DB: {DB_NAME} on {DB_HOST}")
        
        table_query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';
        """
        
        cur.execute(table_query)
        tables = cur.fetchall()
        
        if tables:
            print("\n--- FOUND TABLES ---")
            for table in tables:
                print(f"- {table[0]}")
            print("--------------------\n")
            print("Successfully verified database setup.")
        else:
            print("\n⚠️ No user tables found in the 'public' schema.")
        
        cur.close()

    except Exception as e:
        print(f"\n❌ VERIFICATION ERROR: Failed to query tables.")
        print(f"Details: {e}")

    finally:
        # Close the connection
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    verify_tables()
