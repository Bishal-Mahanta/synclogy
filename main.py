import os
from data.input_handler import load_and_validate
from db.utils import find_existing_products
from spec.tech_scraper import TechScraper
import pandas as pd
import datetime

def process_products(input_filepath, output_filepath):
    # Step 1: Load and validate the user-provided Excel file
    product_df = load_and_validate(input_filepath)
    if product_df is None:
        print("Error in input file. Exiting.")
        return
    
    # Step 2: Check for existing products in the database
    existing_products, missing_products = find_existing_products(product_df)

    # Convert missing_products list to DataFrame for easier processing
    missing_products_df = pd.DataFrame(missing_products)

    # Step 3: Scrape missing products
    scraper = TechScraper(headless_mode=False)  # Set headless mode to False to allow scraping from 91mobiles
    scraped_data = []
    
    for _, product in missing_products_df.iterrows():
        product_name = product['Product Name']
        model_name = product['Model Name']
        category = product['Category'].lower()
        print(f"Scraping product: {product_name} {model_name}")
        
        # For 91mobiles, use the product name and the model name as the search query
        search_query = f"{product_name} {model_name}"

        # Trigger the scraping process
        product_url = scraper.search_product(search_query)
        if product_url:
            product_details = scraper.extract_technical_details(product_url)
            if product_details:
                product_details['category'] = category  # Add category information to the scraped data
                scraped_data.append(product_details)
    
    # Close the scraper
    scraper.close()

    # Step 4: Generate the output Excel file
    # Combine existing products and newly scraped data
    existing_df = pd.DataFrame([product.to_dict() for product in existing_products])
    scraped_df = pd.DataFrame(scraped_data)

    # Concatenate dataframes
    final_df = pd.concat([existing_df, scraped_df], ignore_index=True)

    # Split data by category and write to different sheets
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        if not final_df.empty:
            for category in final_df['category'].unique():
                category_df = final_df[final_df['category'] == category]
                sheet_name = category.capitalize()
                category_df.to_excel(writer, index=False, sheet_name=sheet_name)
    
    print(f"Output generated at {output_filepath}")

if __name__ == "__main__":
    # Input and output file paths
    input_filepath = "data/product_data.xlsx"  # Example input path
    output_filepath = "data/output_product_details.xlsx"  # Example output path

    # Make sure input file exists
    if not os.path.exists(input_filepath):
        print(f"Input file '{input_filepath}' not found.")
    else:
        process_products(input_filepath, output_filepath)
