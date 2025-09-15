import sqlite3
import os

# This script should be run from the project root directory /Users/Amy/ttnw/
DB_FILE = "portfolio_manager/portfolio.db"

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """Checks if a column exists and adds it if it doesn't."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        print(f"Column '{column_name}' not found in '{table_name}'. Adding it...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT 0.0")
        print(f"Successfully added '{column_name}' column.")
    else:
        print(f"Column '{column_name}' already exists in '{table_name}'. No action taken.")

def migrate():
    """Connects to the database and adds the fee and tax columns to the transactions table."""
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file not found at '{DB_FILE}'.")
        return

    conn = None
    try:
        print(f"Connecting to database: {DB_FILE}")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print("-" * 20)
        # Add 'fee' column
        add_column_if_not_exists(cursor, "transactions", "fee", "FLOAT")

        print("-" * 20)
        # Add 'tax' column
        add_column_if_not_exists(cursor, "transactions", "tax", "FLOAT")
        print("-" * 20)

        conn.commit()
        print("\nDatabase migration successful!")

    except sqlite3.Error as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    migrate()
