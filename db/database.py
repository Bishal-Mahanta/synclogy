import sqlite3

DB_PATH = "products.db"

def connect_db():
    """Connects to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def create_products_table():
    """
    Creates the products table with a UNIQUE constraint on product_name, model_name, and color.
    """
    query = """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name VARCHAR NOT NULL,
        model_name VARCHAR,
        color VARCHAR,
        category VARCHAR NOT NULL,
        specifications TEXT,
        source VARCHAR NOT NULL,
        last_updated DATETIME,
        UNIQUE(product_name, model_name, color)
    );
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()
    print("Products table created or updated successfully.")

def update_table_schema():
    """
    Updates the products table schema to add a UNIQUE constraint for product_name, model_name, and color.
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Add UNIQUE constraint if not already present
        cursor.execute("PRAGMA foreign_keys=off;")  # Disable foreign keys temporarily
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products_new AS 
        SELECT * FROM products;
        """)
        cursor.execute("DROP TABLE products;")
        cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name VARCHAR NOT NULL,
            model_name VARCHAR,
            color VARCHAR,
            category VARCHAR NOT NULL,
            specifications TEXT,
            source VARCHAR NOT NULL,
            last_updated DATETIME,
            UNIQUE(product_name, model_name, color)
        );
        """)
        cursor.execute("""
        INSERT INTO products SELECT * FROM products_new;
        """)
        cursor.execute("DROP TABLE products_new;")
        cursor.execute("PRAGMA foreign_keys=on;")  # Re-enable foreign keys
        conn.commit()
        print("Schema updated successfully.")
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()
