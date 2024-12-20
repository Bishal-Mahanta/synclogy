from db.database import connect_db

def save_product_to_db(product):
    """
    Inserts or updates a product in the database.
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
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, product)
    conn.commit()
    conn.close()
