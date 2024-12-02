from db.database import Product, SessionLocal

def find_existing_products(df):
    """Checks if products are already present in the database."""
    session = SessionLocal()
    existing_products = []
    missing_products = []

    try:
        for _, row in df.iterrows():
            product = session.query(Product).filter_by(
                product_name=row['Product Name'],
                model_name=row['Model Name'],
                color=row['Color'],
                category=row['Category']
            ).first()

            if product:
                existing_products.append(product)
            else:
                missing_products.append(row)

    except Exception as e:
        print(f"Error checking products in the database: {e}")
    finally:
        session.close()

    return existing_products, missing_products

def save_product_to_db(product_data):
    """Saves product data to the database."""
    session = SessionLocal()
    try:
        existing_product = session.query(Product).filter_by(
            product_name=product_data['product_name'],
            model_name=product_data['model_name'],
            color=product_data['color'],
            category=product_data['category']
        ).first()

        if existing_product:
            existing_product.specifications = product_data['specifications']
            existing_product.last_updated = datetime.datetime.utcnow()
            print(f"Product '{existing_product.product_name}' updated in the database.")
        else:
            new_product = Product(
                product_name=product_data['product_name'],
                model_name=product_data['model_name'],
                color=product_data['color'],
                category=product_data['category'],
                specifications=product_data['specifications'],
                source=product_data['source']
            )
            session.add(new_product)
            print(f"Product '{new_product.product_name}' added to the database.")

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error saving product to the database: {e}")
    finally:
        session.close()
