import os
import logging
import pandas as pd
from datetime import datetime
from data.input_handler import load_input_data  # Updated import
from spec.flipkart_scraper import FlipkartScraper
from spec.amazon_scraper import AmazonScraper
from spec.tech_scraper import TechScraper
from media.image_scraper import process_excel_file
from media.image_uploader import main as upload_and_save_links
from media.image_styler_and_optimizer import process_images_in_directory
from scripts.price import GoogleShoppingScraper, Product
from scripts.image_mapper import map_images_to_sheets
from scripts.batch_processor import BatchProcessor

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
    product_df = pd.read_excel(input_filepath)  # Directly load data without validation
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

        for _, product in valid_product_df.iterrows():
            product_name = product['Manufacturer']
            link = product.get('Link')  # Check for direct link
            model_name = product['Model Name']
            product_color = product['Color']
            category = product['Category'].lower()

            # If a direct link is provided, use it directly
            if pd.notna(link) and 'flipkart' in link.lower():
                logging.info(f"Using direct link for product: {product_name} {model_name}")
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
                    continue
                except Exception as e:
                    logging.error(f"Error processing direct link for {product_name}: {e}")
            
            # If no direct link, proceed with search
            search_query = None
            if pd.notna(product_color):
                search_query = f"{product_name} {model_name} {product_color}".replace('nan', '').strip()
            else:
                search_query = f"{product_name} {model_name}".replace('nan', '').strip()

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
        product_name = product['Manufacturer']
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


def process_images(input_filepath):
    input_file = "data/output_scraper_results.xlsx"
    if os.path.exists(input_filepath):
        logging.info(f"Processing images from {input_filepath}")
        process_excel_file(input_filepath)
    else:
        logging.error(f"Input file '{input_filepath}' not found.")
        
def upload_images_and_update_links(images_dirpath, image_links_filepath):
    """
    Call the uploader script to upload images to Cloudinary and save their public URLs.
    """
    try:
        # from media.image_uploader import main as upload_and_save_links
        logging.info("Starting image upload and link update process.")
        upload_and_save_links(images_dirpath, image_links_filepath)
        logging.info("Image upload and link update process completed successfully.")
    except Exception as e:
        logging.error(f"Error during image upload and link update: {e}")


def style_and_optimize_images(input_directory):
    # input_directory = "data/output/images"
    logging.info("Starting image styling and optimization...")
    process_images_in_directory(input_directory)
    logging.info("Image styling and optimization completed.")

def process_google_shopping_products(filepath):
    """
    Reads products from an Excel file, fetches their prices from Google Shopping,
    and appends vendor details to the same Excel file.
    """
    if not os.path.exists(filepath):
        logging.error(f"File '{filepath}' not found.")
        return

    try:
        # Load all sheets
        all_sheets = pd.read_excel(filepath, sheet_name=None)

        # Initialize the GoogleShoppingScraper
        scraper = GoogleShoppingScraper(headless=True)
        logging.info("Initialized GoogleShoppingScraper.")

        with pd.ExcelWriter(filepath, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            for sheet_name, sheet_data in all_sheets.items():
                # Skip the "To Be Checked Again" sheet
                if sheet_name == "To Be Checked Again":
                    logging.info(f"Skipping sheet: {sheet_name}")
                    continue

                logging.info(f"Processing sheet: {sheet_name}")
                if sheet_data.empty:
                    logging.warning(f"Sheet '{sheet_name}' is empty. Skipping.")
                    continue

                # Process each product in the sheet
                for index, row in sheet_data.iterrows():
                    product_name = row.get("Product Name")
                    if not product_name:
                        logging.warning(f"Missing product name in sheet '{sheet_name}' row {index}. Skipping.")
                        continue

                    logging.info(f"Scraping Google Shopping for: {product_name}")
                    products = scraper.search_products(product_name)

                    if not products:
                        logging.warning(f"No results found for: {product_name}")
                        continue

                    # Limit results to 10 vendors
                    products = products[:10]

                    # Add new columns dynamically for vendors
                    for product in products:
                        vendor_col_price = f"{product.vendor} Price"
                        vendor_col_url = f"{product.vendor} URL"

                        # Ensure columns exist
                        if vendor_col_price not in sheet_data.columns:
                            sheet_data[vendor_col_price] = None
                        if vendor_col_url not in sheet_data.columns:
                            sheet_data[vendor_col_url] = None

                        # Update row with vendor details
                        sheet_data.loc[index, vendor_col_price] = f"{product.currency}{product.price}"
                        sheet_data.loc[index, vendor_col_url] = product.link

                # Save updated sheet back to the Excel file
                sheet_data.to_excel(writer, index=False, sheet_name=sheet_name)
                logging.info(f"Updated data written to sheet: {sheet_name}")

    except Exception as e:
        logging.error(f"Error processing Google Shopping products: {e}")
    finally:
        scraper.close()

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging to write to both file and console
    log_file = os.path.join(log_dir, f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def setup_file_logging(input_filename):
    """
    Setup logging for individual file processing
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a log file named after the input file
    base_filename = os.path.splitext(input_filename)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{base_filename}_{timestamp}.log")
    
    # Remove any existing handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configure logging with new handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Started processing file: {input_filename}")
    return log_file

# NOTE Main file
def process_single_file(input_filepath):
    """
    Process a single input file through the entire workflow
    """
    try:
        filename = os.path.basename(input_filepath)
        log_file = setup_file_logging(filename)  # Generate log file
        
        # Generate output filenames based on input filename
        base_filename = os.path.splitext(filename)[0]
        output_filepath = f"data/output/output_{base_filename}.xlsx"
        image_links_filepath = f"data/output/image_links_{base_filename}.xlsx"
        
        # Create output directory if it doesn't exist
        os.makedirs("data/output", exist_ok=True)

        # Create images directory if it doesn't exist
        os.makedirs("data/output/images", exist_ok=True)

        images_dirpath = f"data/output/images"
        
        # Initial processing
        logging.info(f"Starting processing for file: {filename}")
        process_flipkart_products(input_filepath, output_filepath)
        process_amazon_and_91mobiles(input_filepath, output_filepath)
        
        # Image processing
        process_images(output_filepath)
        style_and_optimize_images(images_dirpath)
        upload_images_and_update_links(images_dirpath, image_links_filepath)
        
        # Process Google Shopping data
        if os.path.exists(output_filepath):
            process_google_shopping_products(output_filepath)
        
        # Map images and create batch
        if os.path.exists(image_links_filepath):
            if map_images_to_sheets(output_filepath, image_links_filepath):
                processor = BatchProcessor()
                if processor.process_batch(input_filepath, output_filepath, image_links_filepath, log_file, images_dirpath):
                    logging.info(f"Successfully completed processing file: {filename}")
                    return True
            else:
                logging.error(f"Image mapping failed for file: {filename}")
                return False
        else:
            logging.error(f"Image links file not found for: {filename}")
            return False
            
    except Exception as e:
        logging.error(f"Error processing file {filename}: {e}")
        return False


def main():
    """
    Main function to process all Excel files in data/input directory
    """
    input_dir = "data/input"
    
    # Create input directory if it doesn't exist
    os.makedirs(input_dir, exist_ok=True)
    
    # Get all Excel files in the input directory
    excel_files = [f for f in os.listdir(input_dir) 
                  if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$')]
    
    if not excel_files:
        print(f"No Excel files found in {input_dir}")
        return
    
    # Process each file sequentially
    for filename in excel_files:
        input_filepath = os.path.join(input_dir, filename)
        process_single_file(input_filepath)


if __name__ == "__main__":
    # Setup initial basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
