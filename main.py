import os
import logging
import pandas as pd
from data.input_handler import load_and_validate
from spec.flipkart_scraper import FlipkartScraper
from spec.amazon_scraper import AmazonScraper
from spec.tech_scraper import TechScraper
from media.image_scraper import process_excel_file
from media.image_uploader import main as upload_and_save_links


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def append_to_sheet(output_filepath, sheet_name, new_data):
    try:
        if os.path.exists(output_filepath):
            with pd.ExcelWriter(output_filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                try:
                    existing_data = pd.read_excel(output_filepath, sheet_name=sheet_name)
                    combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                    combined_data = combined_data.drop_duplicates(subset=['Product Name'], keep='last')
                except ValueError:  # Sheet does not exist
                    combined_data = new_data

                combined_data.to_excel(writer, index=False, sheet_name=sheet_name)
                logging.info(f"Updated data written to sheet: {sheet_name}")
        else:
            with pd.ExcelWriter(output_filepath, engine='openpyxl', mode='w') as writer:
                new_data.to_excel(writer, index=False, sheet_name=sheet_name)
                logging.info(f"Created new sheet: {sheet_name}")
    except Exception as e:
        logging.error(f"Failed to write data to {sheet_name}: {e}")

def process_flipkart_products(input_filepath, output_filepath):
    product_df = load_and_validate(input_filepath)
    if product_df is None:
        logging.error("Error in input file. Please check the input data and try again.")
        return

    valid_products = []
    for _, row in product_df.iterrows():
        category = row['Category'].lower()
        if category in ['phone', 'mobile']:
            if pd.notna(row['Product Name']) and pd.notna(row['Model Name']) and pd.notna(row['Color']):
                valid_products.append(row)
        elif category in ['computer', 'laptop']:
            if pd.notna(row['Product Name']) and pd.notna(row['Model Name']):
                valid_products.append(row)
        else:
            valid_products.append(row)

    if not valid_products:
        logging.info("No valid products found in the input file.")
        return

    valid_product_df = pd.DataFrame(valid_products)
    not_found_products = []

    if not valid_product_df.empty:
        flipkart_scraper = FlipkartScraper()

        for _, product in valid_product_df.iterrows():
            product_name = product['Product Name']
            model_name = product['Model Name']
            category = product['Category'].lower()

            search_query = f"{product_name} {model_name}"
            if category not in ['computer', 'laptop']:
                color = product.get('Color', '')
                if pd.notna(color) and color.strip():
                    search_query += f" {color}"

            logging.info(f"Searching for product on Flipkart: {search_query}")
            product_links = flipkart_scraper.search_product(search_query)

            if not product_links:
                logging.warning(f"Product not found: {search_query}")
                not_found_products.append(product)
                continue

            for parsed_name, link in product_links:
                logging.info(f"Extracting details for: {parsed_name}")
                product_details = flipkart_scraper.extract_product_details(link)

                additional_table_data = flipkart_scraper.extract_additional_table_data(link)
                if additional_table_data:
                    for table_entry in additional_table_data:
                        product_details[table_entry["Header"]] = table_entry["Data"]

                if product_details:
                    sheet_name = f"All Details {category.capitalize()}"
                    product_details_df = pd.DataFrame([product_details])
                    append_to_sheet(output_filepath, sheet_name, product_details_df)

        flipkart_scraper.close()

    if not_found_products:
        not_found_df = pd.DataFrame(not_found_products)
        append_to_sheet(output_filepath, "To Be Checked Again", not_found_df)
        logging.info("Products not found on Flipkart saved to 'To Be Checked Again'.")

def process_amazon_and_91mobiles(input_filepath, output_filepath):
    if not os.path.exists(output_filepath):
        logging.error(f"Output file '{output_filepath}' not found.")
        return

    try:
        not_found_df = pd.read_excel(output_filepath, sheet_name="To Be Checked Again")
    except ValueError:
        logging.error("'To Be Checked Again' sheet not found.")
        return

    if not_found_df.empty:
        logging.info("No products to process.")
        return

    
    tech_scraper = TechScraper(headless_mode=False)
    amazon_details = []

    for _, product in not_found_df.iterrows():
        product_name = product['Product Name']
        model_name = product.get('Model Name', '')
        search_query = f"{product_name} {model_name}".strip()
        logging.info(f"Processing: {search_query}")

        # Step 1: Use 91mobiles (TechScraper) to get some technical details
        tech_details = {}
        tech_link = tech_scraper.search_product(search_query)
        if tech_link:
            logging.info(f"Found link on 91mobiles: {tech_link}")
            tech_details = tech_scraper.extract_technical_details(tech_link)

        # Step 2: Use Amazon to get more product details
        amazon_scraper = AmazonScraper()
        product_links = amazon_scraper.search_product(search_query)
        if not product_links:
            logging.warning(f"No products found for: {search_query}")
            continue

        for link in product_links:
            general_details = amazon_scraper.extract_product_details(link)
            if tech_details:
                general_details.update(tech_details)

            amazon_details.append(general_details)
            break

    amazon_scraper.close()
    tech_scraper.close()

    if amazon_details:
        amazon_df = pd.DataFrame(amazon_details)
        append_to_sheet(output_filepath, "Amazon Product Details", amazon_df)
        logging.info("Amazon product details saved to 'Amazon Product Details'.")
        
def process_images():
    """
    Process images from the output_scraper_results.xlsx file.
    """
    input_file = "data/output_scraper_results.xlsx"  # File to process
    if os.path.exists(input_file):
        logging.info(f"Processing images from {input_file}")
        process_excel_file(input_file)
    else:
        logging.error(f"Input file '{input_file}' not found.")
        
        
def upload_images_and_update_links():
    """
    Upload images to Hostinger and update the output_scraper_results.xlsx file with their URLs.
    """
    logging.info("Starting image upload and link update process.")
    try:
        upload_and_save_links()
        logging.info("Image upload and link update process completed successfully.")
    except Exception as e:
        logging.error(f"Error during image upload and link update: {e}")


if __name__ == "__main__":
    # input_filepath = "data/product_data.xlsx"  # Example input file path
    # output_filepath = "data/output_scraper_results.xlsx"  # Example output file path

    # if not os.path.exists(input_filepath):
    #     logging.error(f"Input file '{input_filepath}' not found.")
    # else:
    #     process_flipkart_products(input_filepath, output_filepath)
    #     process_amazon_and_91mobiles(input_filepath, output_filepath)
        
    # process_images()
    upload_images_and_update_links()
