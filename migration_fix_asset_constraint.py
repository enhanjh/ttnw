import sqlite3
import os

DB_FILE = "portfolio_manager/portfolio.db"

def migrate():
    """
    Rebuilds the 'assets' table to change the UNIQUE constraint
    from just 'symbol' to a composite of ('symbol', 'portfolio_id').
    """
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file not found at '{DB_FILE}'.")
        return

    conn = None
    try:
        print(f"Connecting to database: {DB_FILE}")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print("Starting transaction...")
        cursor.execute("BEGIN TRANSACTION;")

        # Step 1: Create a new table with the correct schema
        print("Creating new 'assets_new' table with the correct constraints...")
        cursor.execute("""
            CREATE TABLE assets_new (
                id INTEGER NOT NULL, 
                symbol VARCHAR, 
                name VARCHAR, 
                asset_type VARCHAR, 
                portfolio_id INTEGER, 
                PRIMARY KEY (id), 
                FOREIGN KEY(portfolio_id) REFERENCES portfolios (id), 
                UNIQUE (symbol, portfolio_id)
            )
        """)
        print("'assets_new' table created successfully.")

        # Step 2: Copy data from the old table to the new table
        print("Copying data from 'assets' to 'assets_new'...")
        cursor.execute("INSERT INTO assets_new (id, symbol, name, asset_type, portfolio_id) SELECT id, symbol, name, asset_type, portfolio_id FROM assets;")
        print("Data copied successfully.")

        # Step 3: Drop the old table
        print("Dropping the old 'assets' table...")
        cursor.execute("DROP TABLE assets;")
        print("Old 'assets' table dropped.")

        # Step 4: Rename the new table to the original name
        print("Renaming 'assets_new' to 'assets'...")
        cursor.execute("ALTER TABLE assets_new RENAME TO assets;")
        print("Table renamed successfully.")

        # Step 5: Commit the transaction
        print("Committing transaction...")
        conn.commit()
        print("\nDatabase migration successful! The asset constraint has been fixed.")

    except sqlite3.Error as e:
        print(f"\nAn error occurred: {e}")
        if conn:
            print("Rolling back transaction...")
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    migrate()
