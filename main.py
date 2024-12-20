import os
import logging
import pandas as pd
import time
import random
from data.input_handler import load_input_data, find_input_file  # Updated import
from spec.flipkart_scraper import FlipkartScraper
from spec.amazon_scraper import AmazonScraper
from spec.tech_scraper import TechScraper
from media.image_scraper import process_excel_file
from media.image_uploader import main as upload_and_save_links
from media.image_styler_and_optimizer import process_images_in_directory
from scripts.merge_phone_sheets import process_phone_sheets
from db.db_operations import save_products
from db.database import update_table_schema, create_products_table

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
    product_df = pd.read_excel(input_filepath)
    if product_df.empty:
        logging.error("Input file is empty or invalid. Please check the file and try again.")
        return

    valid_products = []
    for _, row in product_df.iterrows():
        category = row['Category'].lower()
        valid_products.append(row)

    if not valid_products:
        logging.info("No valid products found in the input file.")
        return

    valid_product_df = pd.DataFrame(valid_products)
    not_found_products = []

    if not valid_product_df.empty:
        flipkart_scraper = FlipkartScraper()
        flipkart_scraper.driver.get("https://www.flipkart.com")
        time.sleep(random.uniform(3, 6))  # Allow cookies and session setup

        for index, product in valid_product_df.iterrows():
            try:
                logging.info(f"Processing product {index + 1}/{len(valid_product_df)}: {product['Product Name']}")
                product_name = product['Product Name']
                link = product.get('Link')
                model_name = product['Model Name']
                product_color = product['Color']
                category = product['Category'].lower()

                if pd.notna(link) and 'flipkart' in link.lower():
                    logging.info(f"Using direct link for product: {product_name}")
                    try:
                        product_details = flipkart_scraper.extract_product_details(link)
                        additional_table_data = flipkart_scraper.extract_additional_table_data(link)

                        if additional_table_data:
                            for table_entry in additional_table_data:
                                product_details[table_entry["Header"]] = table_entry["Data"]

                        if product_details:
                            sheet_name = f"Flipkart {category.capitalize()} Details"
                            product_details_df = pd.DataFrame([product_details])
                            append_to_sheet(output_filepath, sheet_name, product_details_df)
                    except Exception as e:
                        logging.error(f"Error processing direct link for {product_name}: {e}")
                        continue

                else:
                    if pd.notna(product_color):
                        search_query = f"{product_name} {model_name} {product_color}".strip()
                    else:
                        search_query = f"{product_name} {model_name}".strip()

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
                            sheet_name = f"Flipkart {category.capitalize()} Details"
                            product_details_df = pd.DataFrame([product_details])
                            append_to_sheet(output_filepath, sheet_name, product_details_df)

            except Exception as e:
                logging.error(f"Error processing product {index + 1}: {product['Product Name']}. Error: {e}")
                continue

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
    amazon_scraper = AmazonScraper()
    amazon_details = []

    for _, product in not_found_df.iterrows():
        product_name = product['Product Name']
        link = product.get('Link')  # Check for direct Amazon link
        link_rel = product.get('91 Link')  # Check for 91mobiles link
        model_name = product.get('Model Name', '')
        category = product['Category']
        asin = product.get('Asin')
        search_query = f"{product_name} {model_name}".strip()
        logging.info(f"Processing: {search_query}")

        # Process 91mobiles details first
        tech_details = {}
        if pd.notna(link_rel):
            logging.info(f"Using direct 91mobiles link: {link_rel}")
            try:
                tech_details = tech_scraper.extract_technical_details(link_rel)
            except Exception as e:
                logging.error(f"Error extracting details from 91mobiles link: {e}")
        else:
            # If no direct link, search for 91mobiles link
            tech_link = tech_scraper.search_product(search_query)
            if tech_link:
                logging.info(f"Found link on 91mobiles: {tech_link}")
                try:
                    tech_details = tech_scraper.extract_technical_details(tech_link)
                except Exception as e:
                    logging.error(f"Error extracting details from 91mobiles search: {e}")

        # Process Amazon details
        
        # If direct Amazon link is provided, use it directly
        if pd.notna(link):
            logging.info(f"Using direct Amazon link: {link}")
            try:
                general_details = amazon_scraper.extract_product_details(link)

                # Merge tech details if available
                if tech_details:
                    general_details.update(tech_details)

                amazon_details.append(general_details)
                continue
            except Exception as e:
                logging.error(f"Error extracting Amazon product details from direct link: {e}")

        # If no direct link, search for Amazon link
        if pd.notna(asin):
            logging.info(f"Using Asin: {asin}")
            product_links = amazon_scraper.search_product(asin)
        else:
            product_links = amazon_scraper.search_product(search_query)
            if not product_links:
                logging.warning(f"No products found for: {search_query}")
                continue

        # Process the first matching Amazon link
        for link in product_links:
            try:
                general_details = amazon_scraper.extract_product_details(link)

                # Merge tech details if available
                if tech_details:
                    general_details.update(tech_details)

                amazon_details.append(general_details)
                break
            except Exception as e:
                logging.error(f"Error extracting Amazon product details: {e}")

    amazon_scraper.close()
    tech_scraper.close()

    if amazon_details:
        amazon_df = pd.DataFrame(amazon_details)
        append_to_sheet(output_filepath, f"Amazon {category.capitalize()} Details", amazon_df)
        logging.info("Amazon product details saved to 'Amazon Product Details'.")


def process_images():
    input_file = "data/output_scraper_results.xlsx"
    if os.path.exists(input_file):
        logging.info(f"Processing images from {input_file}")
        process_excel_file(input_file)
    else:
        logging.error(f"Input file '{input_file}' not found.")
        
def upload_images_and_update_links():
    """
    Call the uploader script to upload images to Cloudinary and save their public URLs.
    """
    try:
        from media.image_uploader import main as upload_and_save_links
        logging.info("Starting image upload and link update process.")
        upload_and_save_links()
        logging.info("Image upload and link update process completed successfully.")
    except Exception as e:
        logging.error(f"Error during image upload and link update: {e}")


def style_and_optimize_images():
    input_directory = "output/images"
    logging.info("Starting image styling and optimization...")
    process_images_in_directory(input_directory)
    logging.info("Image styling and optimization completed.")

def merge_phone_details():
    """
    Merge phone details and create the final sheet.
    """
    output_filepath = "data/output_scraper_results.xlsx"
    result_filepath = "data/final_sheet.xlsx"
    image_links_filepath = "data/uploaded_image_links.xlsx"
    try:
        logging.info("Starting the merging process for phone details.")
        process_phone_sheets(output_filepath, result_filepath, image_links_filepath)
        logging.info("Phone details merged successfully.")
    except Exception as e:
        logging.error(f"Error during merging phone details: {e}")


def validate_columns(dataframe, required_columns):
    """
    Checks if all required columns are present in the DataFrame.
    
    Parameters:
        dataframe (DataFrame): Data to validate.
        required_columns (list): List of required column names.
    
    Returns:
        bool: True if all columns are present, False otherwise.
    """
    missing_columns = [col for col in required_columns if col not in dataframe.columns]
    if missing_columns:
        logging.warning(f"Missing columns: {', '.join(missing_columns)}")
        return False
    return True



def save_final_sheet_to_db():
    """
    Reads the final sheet and saves the data to the database.
    """
    final_sheet_path = "data/final_sheet.xlsx"
    source = "Synclogy"
    required_columns = ["Product Name", "Colors"]  # Minimum required columns

    try:
        # Load the final sheet
        data = pd.read_excel(final_sheet_path)
        if data.empty:
            logging.error("Final sheet is empty. Nothing to save.")
            return

        # Validate required columns
        if not validate_columns(data, required_columns):
            logging.error("Required columns are missing. Cannot save to database.")
            return

        # Fill missing optional columns with defaults
        data["Colors"] = data["Colors"].fillna("Unknown")
        data["RAM"] = data["RAM"].fillna("Unknown")
        data["Primary Camera"] = data["Primary Camera"].fillna("Unknown")
        data["Secondary Camera"] = data["Secondary Camera"].fillna("Unknown")

        # **Preprocess Data for Consistency**
        data["Colors"] = data["Colors"].str.title()  # Normalize Colors
        data["RAM"] = data["RAM"].str.replace(" ", "").str.upper()  # Normalize RAM

        logging.info(f"Saving data from {final_sheet_path} to the database.")
        save_products(data, source, category="Phone")  # Save processed data
        logging.info("Data saved to the database successfully.")
    except Exception as e:
        logging.error(f"Error saving data to database: {e}")

if __name__ == "__main__":

    create_products_table()
    update_table_schema()
    
    input_directory = "data/input"
    output_filepath = "data/output_scraper_results.xlsx"


    # Find the most recent input file
    input_filepath = find_input_file(input_directory)
    if not input_filepath:
        logging.error("No valid input file found. Exiting...")
        exit(1)

    # Load and validate input data
    input_data = load_input_data(input_filepath)
    if input_data is None:
        logging.error("Input data validation failed. Exiting...")
        exit(1)

    if not os.path.exists(input_filepath):
        logging.error(f"Input file '{input_filepath}' not found.")
    else:
        process_flipkart_products(input_filepath, output_filepath)
        process_amazon_and_91mobiles(input_filepath, output_filepath)
        
    process_images()
    style_and_optimize_images()  # Style and optimize images
    upload_images_and_update_links()

    merge_phone_details()
    save_final_sheet_to_db()

    logging.info("Synclogy process completed successfully.")