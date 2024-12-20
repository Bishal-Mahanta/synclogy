import sqlite3
from datetime import datetime
import logging
import json

DB_PATH = "products.db"

def connect_db():
    """
    Connects to the SQLite database and returns the connection object.
    """
    return sqlite3.connect(DB_PATH)

def insert_or_update_product(cursor, product):
    """
    Inserts or updates a product record in the database.
    
    Parameters:
        cursor: SQLite cursor object.
        product (dict): Product data to insert or update.
    """
    query = """
    INSERT INTO products (product_name, model_name, color, category, specifications, source, last_updated)
    VALUES (:product_name, :model_name, :color, :category, :specifications, :source, :last_updated)
    ON CONFLICT(product_name, model_name, color)
    DO UPDATE SET
        category = excluded.category,
        specifications = excluded.specifications,
        source = excluded.source,
        last_updated = excluded.last_updated;
    """
    cursor.execute(query, product)



def save_products(dataframe, source, category):
    """
    Saves data from a DataFrame to the database.

    Parameters:
        dataframe (DataFrame): Data to save.
        source (str): Source of the data (e.g., "Amazon", "Flipkart").
        category (str): Product category (e.g., "Phone", "Laptop").
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fill missing columns with defaults
    dataframe["Colors"] = dataframe["Colors"].fillna("Unknown")
    dataframe["RAM"] = dataframe["RAM"].fillna("Unknown")
    dataframe["Primary Camera"] = dataframe["Primary Camera"].fillna("Unknown")
    dataframe["Secondary Camera"] = dataframe["Secondary Camera"].fillna("Unknown")

    for _, row in dataframe.iterrows():
        # Extract dynamic specifications
        specifications = row.drop(["Product Name", "Model Name", "Colors"], errors="ignore").to_dict()
        
        product = {
            "product_name": row.get("Product Name", "Unknown"),
            "model_name": row.get("Model Name", "Unknown"),
            "color": row.get("Colors", "Unknown"),
            "category": category,
            "specifications": json.dumps(specifications),
            "source": source,
            "last_updated": datetime.now().isoformat()
        }
        try:
            insert_or_update_product(cursor, product)
        except Exception as e:
            logging.error(f"Error inserting product '{row.get('Product Name', 'Unnamed Product')}': {e}")

    conn.commit()
    conn.close()
