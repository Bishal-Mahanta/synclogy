import pandas as pd

def create_sample_input(filepath):
    data = {
        'Product Name': ['Apple iPhone', 'Samsung Galaxy', 'Dell Inspiron', 'HP Pavilion', 'Motorola Edge'],
        'Model Name': ['13 Pro Max', 'S21 Ultra', '15 5000', 'X360', '20 Pro'],
        'Color': ['Black', 'Silver', 'Black', 'Blue', 'White'],
        'Category': ['Phone', 'Phone', 'Laptop', 'Laptop', 'Phone']
    }
    df = pd.DataFrame(data)
    
    # Save to an Excel file
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Product List')

if __name__ == "__main__":
    create_sample_input("data/product_data.xlsx")
    print("Sample input Excel file created successfully.")
